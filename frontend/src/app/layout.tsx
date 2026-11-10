import type { Metadata } from 'next';
import './globals.css';
import { Sidebar } from '@/components/Sidebar';

export const metadata: Metadata = {
  title: 'AgentShield | Intelligence Behind Every Transaction',
  description: 'Autonomous Multi-Agent Payment Fraud Investigation & Prevention Platform with PayPal Sandbox Integration',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-slate-950 text-slate-100 min-h-screen flex antialiased">
        <Sidebar />
        <div className="flex-1 ml-64 flex flex-col min-h-screen bg-slate-950 overflow-x-hidden">
          {children}
        </div>
      </body>
    </html>
  );
}
