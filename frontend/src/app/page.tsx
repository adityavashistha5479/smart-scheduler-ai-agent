import VoiceAgent from "@/components/VoiceAgent";

export default function Home() {
  return (
    <main className="min-h-screen bg-black flex flex-col items-center justify-center p-4 relative overflow-hidden">
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute -top-[40%] -left-[10%] w-[70%] h-[70%] rounded-full bg-purple-900/20 blur-[120px]" />
        <div className="absolute top-[60%] -right-[10%] w-[60%] h-[60%] rounded-full bg-blue-900/20 blur-[120px]" />
      </div>
      
      <div className="z-10 text-center mb-12">
        <h1 className="text-5xl md:text-7xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-emerald-400 tracking-tight">
          Smart Scheduler
        </h1>
        <p className="mt-4 text-xl text-zinc-400 max-w-2xl mx-auto">
          Talk to your AI agent to find the perfect meeting time.
        </p>
      </div>

      <div className="z-10 w-full relative">
        <VoiceAgent />
      </div>
    </main>
  );
}
