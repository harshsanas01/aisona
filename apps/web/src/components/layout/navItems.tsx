import { ClipboardCheck, Phone, ShieldAlert, Sparkles, UploadCloud, type LucideIcon } from 'lucide-react';

export interface NavItem {
  path: string;
  label: string;
  icon: LucideIcon;
  title: string;
  subtitle: string;
}

export const NAV_ITEMS: NavItem[] = [
  {
    path: '/ask',
    label: 'Ask',
    icon: Sparkles,
    title: 'Ask a question',
    subtitle: 'Ask natural-language questions across care-call transcripts and inspect grounded source evidence.',
  },
  {
    path: '/calls',
    label: 'Calls',
    icon: Phone,
    title: 'Calls',
    subtitle: 'Search and browse every ingested care-call transcript.',
  },
  {
    path: '/safety-events',
    label: 'Safety Events',
    icon: ShieldAlert,
    title: 'Safety events',
    subtitle: 'Operational triage flags surfaced across recent calls - not a medical diagnosis.',
  },
  {
    path: '/ingestion',
    label: 'Ingestion',
    icon: UploadCloud,
    title: 'Ingestion',
    subtitle: 'Load new call transcripts into the corpus and confirm they become searchable.',
  },
  {
    path: '/evaluations',
    label: 'Evaluations',
    icon: ClipboardCheck,
    title: 'Evaluations',
    subtitle: 'Answer-quality and retrieval evaluation tooling.',
  },
];
