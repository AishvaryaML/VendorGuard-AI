import React from 'react';

interface PageHeaderProps {
  title: string;
  description: string;
  action?: React.ReactNode;
  badge?: string;
}

export const PageHeader: React.FC<PageHeaderProps> = ({ title, description, action, badge }) => {
  return (
    <div className="flex flex-col md:flex-row md:items-center justify-between pb-6 border-b border-border mb-6 gap-4">
      <div>
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold tracking-tight text-white">{title}</h1>
          {badge && (
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-cyber-cyan/10 text-cyber-cyan border border-cyber-cyan/30">
              {badge}
            </span>
          )}
        </div>
        <p className="text-sm text-slate-400 mt-1">{description}</p>
      </div>
      {action && <div>{action}</div>}
    </div>
  );
};
