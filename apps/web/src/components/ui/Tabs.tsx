interface TabItem {
  id: string;
  label: string;
}

interface TabsProps {
  tabs: TabItem[];
  activeId: string;
  onChange: (id: string) => void;
  idPrefix: string;
}

export function Tabs({ tabs, activeId, onChange, idPrefix }: TabsProps) {
  return (
    <div className="tabs-list" role="tablist">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          type="button"
          role="tab"
          id={`${idPrefix}-tab-${tab.id}`}
          aria-selected={activeId === tab.id}
          aria-controls={`${idPrefix}-panel-${tab.id}`}
          className="tab-trigger"
          onClick={() => onChange(tab.id)}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}

export function TabPanel({ id, idPrefix, activeId, children }: { id: string; idPrefix: string; activeId: string; children: React.ReactNode }) {
  if (id !== activeId) return null;
  return (
    <div
      className="tab-panel"
      role="tabpanel"
      id={`${idPrefix}-panel-${id}`}
      aria-labelledby={`${idPrefix}-tab-${id}`}
    >
      {children}
    </div>
  );
}
