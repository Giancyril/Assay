import React from "react";
import { EvidenceQuote as EvidenceQuoteType } from "../types";
import { CheckCircle2, AlertTriangle } from "lucide-react";

interface EvidenceQuoteProps {
  evidence: EvidenceQuoteType | null;
  onJumpToOffset?: (page: number, start: number, end: number) => void;
}

export const EvidenceQuote: React.FC<EvidenceQuoteProps> = ({ evidence, onJumpToOffset }) => {
  if (!evidence) {
    return (
      <div className="p-3 bg-slate-50 border border-slate-200 rounded-sm text-xs text-slate-500 italic">
        No direct source quote extracted. Check rule condition or absence search trace below.
      </div>
    );
  }

  return (
    <div className="p-3 bg-white border border-slate-200 rounded-sm shadow-2xs space-y-2">
      <div className="flex items-center justify-between text-xs text-slate-500 pb-1 border-b border-slate-100">
        <div className="flex items-center space-x-1.5">
          {evidence.verified ? (
            <span className="inline-flex items-center text-emerald-700 font-medium">
              <CheckCircle2 className="w-3.5 h-3.5 mr-1 text-emerald-600" />
              Verified in source
            </span>
          ) : (
            <span className="inline-flex items-center text-amber-700 font-medium">
              <AlertTriangle className="w-3.5 h-3.5 mr-1 text-amber-600" />
              Unverified quote
            </span>
          )}
        </div>
        <div className="font-mono text-[11px] text-slate-400">
          Page {evidence.page_number} &bull; Offset [{evidence.char_start}..{evidence.char_end}]
        </div>
      </div>
      <blockquote
        className="document-prose text-xs text-slate-800 pl-3 border-l-2 border-slate-400 italic bg-slate-50/50 py-1 cursor-pointer hover:bg-slate-100/50 transition-colors"
        onClick={() => onJumpToOffset?.(evidence.page_number, evidence.char_start, evidence.char_end)}
        title="Click to jump to passage in document"
      >
        "{evidence.verbatim_quote}"
      </blockquote>
    </div>
  );
};
