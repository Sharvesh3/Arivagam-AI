import { FileText, ExternalLink } from 'lucide-react';
import { Source } from '../../services/api';

interface SourceCardProps {
  source: Source;
}

export default function SourceCard({ source }: SourceCardProps) {
  return (
    <div className="bg-white rounded-lg p-3 border border-gray-200 hover:border-primary-300 transition-colors">
      <div className="flex items-start space-x-2">
        <FileText className="w-4 h-4 text-gray-400 mt-0.5 flex-shrink-0" />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-900 truncate">
            {source.document}
          </p>
          <div className="flex items-center space-x-2 mt-1">
            {source.page && (
              <span className="text-xs text-gray-500">Page {source.page}</span>
            )}
            {source.section && (
              <>
                <span className="text-xs text-gray-300">•</span>
                <span className="text-xs text-gray-500 truncate">
                  {source.section}
                </span>
              </>
            )}
          </div>
        </div>
        <button
          className="text-gray-400 hover:text-primary-600 transition-colors"
          title="View source"
        >
          <ExternalLink className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}