import React from 'react';
import { Construction, Sparkles } from 'lucide-react';

interface PlaceholderProps {
  title: string;
  description: string;
}

export default function PlaceholderPage({ title, description }: PlaceholderProps) {
  return (
    <div className="p-8 h-full w-full flex items-center justify-center">
      <div className="max-w-md w-full bg-white border border-slate-200 rounded-3xl p-10 text-center shadow-sm">
        <div className="w-20 h-20 bg-blue-50 text-blue-600 rounded-2xl flex items-center justify-center mx-auto mb-6 transform rotate-3">
          <Construction size={40} />
        </div>
        <h1 className="text-2xl font-extrabold text-slate-900 mb-3">{title}</h1>
        <p className="text-slate-500 font-medium mb-8 leading-relaxed">
          {description}
        </p>
        <div className="bg-slate-50 rounded-xl p-4 flex items-center justify-center gap-3 border border-slate-100 text-sm font-bold text-slate-600">
          <Sparkles size={16} className="text-blue-500" />
          Module Activation Pending
        </div>
      </div>
    </div>
  );
}
