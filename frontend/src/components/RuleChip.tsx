import React from "react";

interface RuleChipProps {
  code: string;
  name: string;
}

export const RuleChip: React.FC<RuleChipProps> = ({ code, name }) => {
  return (
    <div className="inline-flex items-center space-x-1.5 text-xs text-slate-700 bg-slate-100 border border-slate-200 px-2 py-0.5 rounded-sm">
      <span className="font-mono text-[11px] font-semibold text-slate-900">{code}</span>
      <span className="text-slate-400">|</span>
      <span className="truncate max-w-[200px]">{name}</span>
    </div>
  );
};
