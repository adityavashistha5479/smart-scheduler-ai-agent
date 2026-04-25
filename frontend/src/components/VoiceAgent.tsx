"use client";

import React, { useState, useEffect, useRef } from 'react';
import { Mic, MicOff, Calendar, ExternalLink } from 'lucide-react';
import { motion } from 'framer-motion';

// Worklet code to capture PCM16
const processorCode = `
class PCMProcessor extends AudioWorkletProcessor {
  process(inputs, outputs, parameters) {
    const input = inputs[0];
    if (input.length > 0) {
      const channelData = input[0];
      const pcm16 = new Int16Array(channelData.length);
      for (let i = 0; i < channelData.length; i++) {
        const s = Math.max(-1, Math.min(1, channelData[i]));
        pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
      }
      this.port.postMessage(pcm16);
    }
    return true;
  }
}
registerProcessor('pcm-processor', PCMProcessor);
`;

export default function VoiceAgent() {
  const [isConnected, setIsConnected] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [status, setStatus] = useState("Click to connect");
  const [meeting, setMeeting] = useState<any>(null);
  const ws = useRef<WebSocket | null>(null);
  
  // Recording
  const audioContext = useRef<AudioContext | null>(null);
  const workletNode = useRef<AudioWorkletNode | null>(null);
  const mediaStream = useRef<MediaStream | null>(null);

  // Playback
  const playbackContext = useRef<AudioContext | null>(null);
  const nextStartTime = useRef<number>(0);

  const connect = async () => {
    try {
      setStatus("Connecting...");
      const isProd = process.env.NODE_ENV === 'production';
      const defaultUrl = isProd 
        ? 'wss://smart-scheduler-backend-269634872417.asia-southeast2.run.app/ws' 
        : 'ws://localhost:8000/ws';
      const wsUrl = process.env.NEXT_PUBLIC_WS_URL || defaultUrl;
      ws.current = new WebSocket(wsUrl);
      
      ws.current.onopen = () => {
        setIsConnected(true);
        setStatus("Connected. Tap to speak.");
        // Send timezone context to backend for accurate scheduling
        ws.current?.send(JSON.stringify({
          type: "client_init",
          timezone: Intl.DateTimeFormat().resolvedOptions().timeZone
        }));
      };

      ws.current.onmessage = async (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'response.audio.delta' && data.delta) {
          playAudio(data.delta);
        } else if (data.type === 'response.function_call_arguments.done') {
          setStatus(`Agent is checking: ${data.name}...`);
        } else if (data.type === 'response.done') {
          setStatus("Connected. Tap to speak.");
        } else if (data.type === 'error') {
          setStatus(`Error: ${data.error?.message || data.message || "Unknown error"}`);
        } else if (data.type === 'meeting_scheduled') {
          setMeeting(data);
          setStatus("Meeting scheduled successfully!");
        }
      };

      ws.current.onclose = () => {
        setIsConnected(false);
        setIsRecording(false);
        stopRecording();
        setStatus("Disconnected");
      };

    } catch (error) {
      console.error(error);
      setStatus("Connection failed");
    }
  };

  const playAudio = async (base64Audio: string) => {
    if (!playbackContext.current) {
      // Initialize with 24kHz which OpenAI Realtime expects
      playbackContext.current = new window.AudioContext({ sampleRate: 24000 });
      nextStartTime.current = playbackContext.current.currentTime;
    }

    const binaryString = window.atob(base64Audio);
    const len = binaryString.length;
    const bytes = new Uint8Array(len);
    for (let i = 0; i < len; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }
    const int16Array = new Int16Array(bytes.buffer);

    // Convert Int16 to Float32 for Web Audio API
    const float32Array = new Float32Array(int16Array.length);
    for (let i = 0; i < int16Array.length; i++) {
      float32Array[i] = int16Array[i] / 0x7FFF;
    }

    const audioBuffer = playbackContext.current.createBuffer(1, float32Array.length, 24000);
    audioBuffer.copyToChannel(float32Array, 0);

    const source = playbackContext.current.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(playbackContext.current.destination);
    
    // Gapless playback
    const currentTime = playbackContext.current.currentTime;
    const startTime = Math.max(nextStartTime.current, currentTime);
    source.start(startTime);
    nextStartTime.current = startTime + audioBuffer.duration;
  };

  const startRecording = async () => {
    try {
      // 24kHz is required by OpenAI Realtime
      audioContext.current = new window.AudioContext({ sampleRate: 24000 });
      mediaStream.current = await navigator.mediaDevices.getUserMedia({ audio: true });
      
      const source = audioContext.current.createMediaStreamSource(mediaStream.current);
      
      const blob = new Blob([processorCode], { type: 'application/javascript' });
      const url = URL.createObjectURL(blob);
      await audioContext.current.audioWorklet.addModule(url);
      
      workletNode.current = new AudioWorkletNode(audioContext.current, 'pcm-processor');
      
      workletNode.current.port.onmessage = (event) => {
        const pcm16 = event.data; // Int16Array
        if (ws.current?.readyState === WebSocket.OPEN) {
          // Convert Int16Array to base64
          const bytes = new Uint8Array(pcm16.buffer);
          let binary = '';
          for (let i = 0; i < bytes.byteLength; i++) {
            binary += String.fromCharCode(bytes[i]);
          }
          const base64 = window.btoa(binary);
          
          ws.current.send(JSON.stringify({
            type: "input_audio_buffer.append",
            audio: base64
          }));
        }
      };

      source.connect(workletNode.current);
      workletNode.current.connect(audioContext.current.destination);
      
      setIsRecording(true);
      setStatus("Listening...");
    } catch (err) {
      console.error("Recording error:", err);
      setStatus("Microphone error");
    }
  };

  const stopRecording = () => {
    setIsRecording(false);
    if (workletNode.current) {
      workletNode.current.disconnect();
      workletNode.current = null;
    }
    if (mediaStream.current) {
      mediaStream.current.getTracks().forEach(track => track.stop());
      mediaStream.current = null;
    }
    if (audioContext.current) {
      audioContext.current.close();
      audioContext.current = null;
    }
  };

  const toggleRecording = async () => {
    if (!isConnected) {
      await connect();
      return;
    }

    if (isRecording) {
      stopRecording();
      setStatus("Connected. Tap to speak.");
      // Commit audio
      ws.current?.send(JSON.stringify({ type: "input_audio_buffer.commit" }));
      ws.current?.send(JSON.stringify({ type: "response.create" }));
    } else {
      await startRecording();
    }
  };

  return (
    <div className="flex flex-col items-center justify-center p-8 bg-zinc-900 rounded-3xl shadow-2xl border border-zinc-800 max-w-md w-full mx-auto mt-20 relative overflow-hidden">
      <div className="mb-8 text-center z-10">
        <h2 className="text-2xl font-bold text-white mb-2">Smart Scheduler</h2>
        <p className="text-zinc-400 min-h-[1.5rem]">{status}</p>
      </div>

      <motion.button
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        onClick={toggleRecording}
        className={`z-10 w-32 h-32 rounded-full flex items-center justify-center shadow-lg transition-colors cursor-pointer ${
          isRecording 
            ? 'bg-red-500 hover:bg-red-600 shadow-red-500/50' 
            : isConnected
              ? 'bg-emerald-500 hover:bg-emerald-600 shadow-emerald-500/50'
              : 'bg-blue-500 hover:bg-blue-600 shadow-blue-500/50'
        }`}
      >
        {isRecording ? (
          <Mic className="w-12 h-12 text-white animate-pulse" />
        ) : (
          <MicOff className="w-12 h-12 text-white" />
        )}
      </motion.button>

      {/* Audio Visualizer Placeholder */}
      <div className="mt-12 flex items-center gap-1 h-12 z-10">
        {[...Array(5)].map((_, i) => (
          <motion.div
            key={i}
            animate={{
              height: isRecording ? ["20%", "100%", "20%"] : "20%",
            }}
            transition={{
              duration: 0.8,
              repeat: Infinity,
              delay: i * 0.1,
              ease: "easeInOut"
            }}
            className={`w-2 rounded-full ${isRecording ? 'bg-red-400' : 'bg-zinc-600'}`}
            style={{ height: '20%' }}
          />
        ))}
      </div>

      {/* Glow Effect */}
      {isRecording && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 0.5 }}
          className="absolute inset-0 bg-red-500/10 rounded-3xl pointer-events-none blur-2xl"
        />
      )}

      {/* Meeting Preview */}
      {meeting && (
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mt-8 p-4 bg-zinc-800/80 rounded-2xl border border-zinc-700 w-full z-10"
        >
          <div className="flex items-start gap-3">
            <div className="p-2 bg-blue-500/20 rounded-lg text-blue-400">
              <Calendar className="w-6 h-6" />
            </div>
            <div className="flex-1 overflow-hidden">
              <h3 className="text-white font-semibold truncate">{meeting.summary}</h3>
              <p className="text-zinc-400 text-sm mt-1">
                {new Date(meeting.start).toLocaleString()}
              </p>
              <a 
                href={meeting.link} 
                target="_blank" 
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 mt-3 text-sm text-blue-400 hover:text-blue-300 transition-colors"
              >
                View on Calendar <ExternalLink className="w-3 h-3" />
              </a>
            </div>
          </div>
        </motion.div>
      )}
    </div>
  );
}
