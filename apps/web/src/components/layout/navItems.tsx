import {
  CheckSquare, ClipboardCheck, FileText, FlaskConical, Phone, ShieldAlert, Sparkles, UploadCloud, Users,
  type LucideIcon,
} from 'lucide-react';

export interface NavItem {
  path: string;
  label: string;
  icon: LucideIcon;
  title: string;
  subtitle: string;
  /** Only shown when the API reports developer_mode enabled. */
  devOnly?: boolean;
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
    path: '/patients',
    label: 'Patients',
    icon: Users,
    title: 'Patients',
    subtitle: 'Longitudinal patient timelines built from observed transcript events - not diagnosis.',
  },
  {
    path: '/action-center',
    label: 'Action Center',
    icon: CheckSquare,
    title: 'Action Center',
    subtitle: 'Coordinator follow-up tasks - created manually or suggested from transcript evidence.',
  },
  {
    path: '/briefs',
    label: 'Briefs',
    icon: FileText,
    title: 'Care Briefs',
    subtitle: 'Grounded daily/weekly operational summaries, built from already-extracted events, patterns, and tasks.',
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
  {
    path: '/retrieval-lab',
    label: 'Retrieval Lab',
    icon: FlaskConical,
    title: 'Retrieval Comparison Lab',
    subtitle: 'Compare lexical, semantic, hybrid, and hybrid+rerank retrieval on the same question.',
    devOnly: true,
  },
];
