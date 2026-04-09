import type { Metadata } from 'next';
import './globals.css';
import { Toaster } from '@/components/ui/toaster';
import { cn } from '@/lib/utils';
import { Sidebar } from '@/components/layout/Sidebar';
import { Header } from '@/components/layout/Header';
import { SidebarProvider } from '@/components/ui/sidebar';

export const metadata: Metadata = {
  title: 'Ethereal Intelligence',
  description: 'An intelligent chat interface for Gemini models with tool integration.',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Manrope:wght@600;700;800&display=swap"
          rel="stylesheet"
        />
        <link
          href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className={cn("font-body text-on-surface bg-background min-h-screen selection:bg-primary/30 antialiased overflow-hidden")}>
        {/* The Living Canvas Background (Persistent) */}
        <div className="fixed inset-0 -z-10 overflow-hidden living-canvas-bg opacity-30">
          <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] rounded-full bg-primary/10 blur-[120px]"></div>
          <div className="absolute bottom-[10%] right-[-5%] w-[30%] h-[30%] rounded-full bg-secondary/5 blur-[100px]"></div>
        </div>

        <div className="flex h-screen overflow-hidden relative">
          <SidebarProvider>
            <Sidebar />
            <div className="flex-1 flex flex-col relative overflow-hidden">
              <Header />
              {children}
            </div>
          </SidebarProvider>
        </div>
        <Toaster />
      </body>
    </html>
  );
}
