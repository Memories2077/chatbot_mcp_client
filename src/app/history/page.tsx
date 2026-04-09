"use client";

export default function HistoryPage() {
  return (
    <main className="flex-1 overflow-y-auto px-8 pb-12 pt-4 scroll-smooth">
      <div className="max-w-6xl mx-auto mb-12">
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-8 mb-10">
          <div>
            <h2 className="text-5xl font-black text-on-surface font-headline tracking-tighter mb-4">
              Archives.
            </h2>
            <p className="text-on-surface-variant text-lg font-medium opacity-90 max-w-md font-body">
              Your collective intelligence stored in a living repository of
              thoughts and generations.
            </p>
          </div>
          <div className="relative w-full md:w-96 group">
            <div className="absolute inset-y-0 left-5 flex items-center pointer-events-none text-outline group-focus-within:text-secondary transition-colors">
              <span className="material-symbols-outlined">search</span>
            </div>
            <input
              className="w-full bg-surface-container-highest/80 backdrop-blur-md border border-outline-variant/10 rounded-full py-4 pl-14 pr-6 text-on-surface placeholder:text-on-surface-variant focus:ring-2 focus:ring-secondary/20 transition-all outline-none"
              placeholder="Search sessions, keywords, or results..."
              type="text"
            />
          </div>
        </div>

        {/* History Grid (Bento Style) */}
        <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
          {/* Featured / Recent Session */}
          <div className="md:col-span-8 group relative overflow-hidden rounded-xl bg-surface-container-low hover:bg-surface-container transition-all duration-500 p-8 flex flex-col justify-between h-[400px] border border-outline-variant/5">
            <div className="absolute top-0 right-0 p-8">
              <span className="bg-primary/10 text-primary px-4 py-1 rounded-full text-xs font-bold uppercase tracking-wider">
                Most Recent
              </span>
            </div>
            <div className="relative z-10">
              <span className="text-on-surface-variant text-xs font-bold uppercase tracking-wider block mb-4">
                Yesterday, 11:42 PM
              </span>
              <h3 className="text-3xl font-bold font-headline text-on-surface max-w-lg mb-4 leading-tight">
                Neural Architecture Synthesis for Bio-mimetic Urban Planning
              </h3>
              <p className="text-on-surface-variant text-lg font-medium opacity-90 max-w-md line-clamp-2 font-body">
                Exploration of self-sustaining architectural modules inspired by mycelium networks and carbon sequestration...
              </p>
            </div>
            <div className="flex items-center gap-4 mt-8">
              <div className="flex -space-x-3">
                <div className="w-8 h-8 rounded-full border-2 border-surface-container-low bg-primary/20 flex items-center justify-center">
                  <span className="material-symbols-outlined text-[10px]">token</span>
                </div>
                <div className="w-8 h-8 rounded-full border-2 border-surface-container-low bg-secondary/20 flex items-center justify-center">
                  <span className="material-symbols-outlined text-[10px]">psychology</span>
                </div>
              </div>
              <span className="text-on-surface-variant text-xs font-bold uppercase tracking-wider">
                1.2k tokens • 24 messages
              </span>
              <button className="ml-auto flex items-center gap-2 text-primary font-semibold hover:gap-4 transition-all">
                Resume Session
                <span className="material-symbols-outlined">arrow_forward</span>
              </button>
            </div>
            <div className="absolute -bottom-20 -right-20 w-80 h-80 bg-primary/5 rounded-full blur-[80px] group-hover:bg-primary/10 transition-colors"></div>
          </div>

          {/* Secondary Session */}
          <div className="md:col-span-4 rounded-xl bg-surface-variant/40 backdrop-blur-md p-8 flex flex-col h-[400px] border border-outline-variant/5">
            <span className="text-on-surface-variant text-xs font-bold uppercase tracking-wider mb-2">
              OCT 14
            </span>
            <h3 className="text-xl font-bold font-headline text-on-surface mb-4">
              Abstract UI Refinement
            </h3>
            <div className="flex-1 relative mb-6 overflow-hidden rounded-lg">
              <img
                alt="UI Concept"
                className="w-full h-full object-cover"
                src="https://lh3.googleusercontent.com/aida-public/AB6AXuC0dqkZBMWeAGiihikjstR9zKRVS2_5TYkBSWi8PcSL4BfLtbbKkJrqVfFeOKO6vwcP4A0LeNVzadlUamfoqycA_0tNO9g0RHHE24cpKFiFfGgOBdfs0jtkADYiAX6xw5Bj2qw3Ronq9i6-yy3hEArzWXNbT6DGsYVb9kIYYMzY1PgnoQHq89C1CAJGk-MsNKRpukbXPN2ozPdkHBtfIMlY8FOPG8z9DNRn7sV9L5I3QsBYzIH2OJV6TW962giOgxwoew9ndmohN-B4"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-surface-variant/80 to-transparent"></div>
            </div>
            <button className="w-full py-3 bg-surface-container-highest rounded-xl text-on-surface text-xs font-bold uppercase tracking-wider hover:bg-surface-bright transition-colors">
              View Assets
            </button>
          </div>

          {/* Row 2: List Style Entries */}
          <div className="md:col-span-6 bg-surface-container-low rounded-xl p-6 flex items-start gap-6 hover:bg-surface-container transition-all border border-outline-variant/5">
            <div className="w-16 h-16 rounded-2xl bg-tertiary/10 flex items-center justify-center flex-shrink-0 text-tertiary">
              <span className="material-symbols-outlined text-3xl">code</span>
            </div>
            <div className="flex-1">
              <div className="flex justify-between items-start mb-1">
                <h4 className="font-bold text-on-surface font-headline">React Component Refactoring</h4>
                <span className="text-xs text-on-surface-variant">2 days ago</span>
              </div>
              <p className="text-on-surface-variant text-sm line-clamp-2 mb-3 font-body">
                Optimizing high-order components for the new design system implementation...
              </p>
              <div className="flex gap-2">
                <span className="px-2 py-0.5 rounded bg-surface-container text-[10px] uppercase font-bold text-outline">Frontend</span>
                <span className="px-2 py-0.5 rounded bg-surface-container text-[10px] uppercase font-bold text-outline">Refactor</span>
              </div>
            </div>
          </div>

          <div className="md:col-span-6 bg-surface-container-low rounded-xl p-6 flex items-start gap-6 hover:bg-surface-container transition-all border border-outline-variant/5">
            <div className="w-16 h-16 rounded-2xl bg-secondary/10 flex items-center justify-center flex-shrink-0 text-secondary">
              <span className="material-symbols-outlined text-3xl">auto_awesome</span>
            </div>
            <div className="flex-1">
              <div className="flex justify-between items-start mb-1">
                <h4 className="font-bold text-on-surface font-headline">Marketing Tagline Ideation</h4>
                <span className="text-xs text-on-surface-variant">Oct 12</span>
              </div>
              <p className="text-on-surface-variant text-sm line-clamp-2 mb-3 font-body">
                Brainstorming punchy hooks for the Ethereal Intelligence launch campaign...
              </p>
              <div className="flex gap-2">
                <span className="px-2 py-0.5 rounded bg-surface-container text-[10px] uppercase font-bold text-outline">Creative</span>
                <span className="px-2 py-0.5 rounded bg-surface-container text-[10px] uppercase font-bold text-outline">Marketing</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
