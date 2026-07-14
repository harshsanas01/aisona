import { useState } from 'react';
import { Terminal, FileJson, Info } from 'lucide-react';
import { Card } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Tabs, TabPanel } from '../../components/ui/Tabs';
import './evaluations.css';

interface EvalLayer {
  id: string;
  label: string;
  command: string;
  script: string;
  description: string;
  metrics: string[];
  outputShape: string;
}

const LAYERS: EvalLayer[] = [
  {
    id: 'hit-rate',
    label: 'Hit-rate',
    command: 'python scripts/evaluate.py',
    script: 'scripts/evaluate.py',
    description: 'Runs every question in data/evaluation/carecall_questions.json through the live container and checks that every expected source call was cited.',
    metrics: ['Per-question PASS/FAIL', 'Overall grounding accuracy (N / total questions)'],
    outputShape: `<question_id> PASS|FAIL expected=[...] cited=[...]
...
Retrieval grounding accuracy: <passed>/<total>`,
  },
  {
    id: 'retrieval',
    label: 'Retrieval metrics',
    command: 'python scripts/evaluate_retrieval.py',
    script: 'scripts/evaluate_retrieval.py',
    description: 'Finer-grained retrieval scoring: recall, precision, mean reciprocal rank, and unanswerable-question accuracy. Writes artifacts/retrieval_evaluation.json.',
    metrics: ['Hit rate', 'Mean recall', 'Mean precision', 'Mean reciprocal rank', 'Unanswerable accuracy', 'Per-question recall/precision/RR + expected vs cited calls'],
    outputShape: `{
  "per_question": [
    { "question_id", "expected", "cited", "answerable",
      "recall", "precision", "reciprocal_rank", "hit" }
  ],
  "aggregate": {
    "hit_rate", "mean_recall", "mean_precision",
    "mean_reciprocal_rank", "unanswerable_accuracy"
  }
}`,
  },
  {
    id: 'grounding',
    label: 'Grounded-answer checks',
    command: 'python scripts/evaluate_grounding.py',
    script: 'scripts/evaluate_grounding.py',
    description: 'Structural/lexical fact-checks (not an LLM judge): every citation references a real call and in-bounds turns, quotes are real, unanswerable responses carry no citations, and adversarial "forbidden source" misattribution never happens. Writes artifacts/grounding_evaluation.json.',
    metrics: ['Per-question PASS/FAIL with problem list', 'Grounded-answer pass count (passed / total)', 'Covers both the original and adversarial question sets'],
    outputShape: `[original|adversarial] <question_id> PASS|FAIL - <problems if any>
...
Grounded-answer evaluation: <passed>/<total>`,
  },
];

export function EvaluationsPage() {
  const [activeId, setActiveId] = useState(LAYERS[0].id);

  return (
    <div className="content-max evaluations-page">
      <Card padding="sm" className="eval-notice">
        <Info size={16} aria-hidden="true" />
        <span>
          The API does not currently expose evaluation results, so this page documents the real CLI tooling
          instead of showing invented numbers. Run a layer locally to see live results.
        </span>
      </Card>

      <Card padding="md">
        <div className="eval-run-all">
          <Terminal size={16} aria-hidden="true" />
          <code>make eval</code>
          <span>runs all three layers below in sequence.</span>
        </div>

        <Tabs
          idPrefix="eval"
          tabs={LAYERS.map((layer) => ({ id: layer.id, label: layer.label }))}
          activeId={activeId}
          onChange={setActiveId}
        />

        {LAYERS.map((layer) => (
          <TabPanel key={layer.id} id={layer.id} idPrefix="eval" activeId={activeId}>
            <p className="eval-description">{layer.description}</p>

            <div className="eval-command-row">
              <Terminal size={14} aria-hidden="true" />
              <code>{layer.command}</code>
            </div>

            <h3 className="eval-subheading">Metrics reported</h3>
            <div className="eval-metric-chips">
              {layer.metrics.map((metric) => <Badge key={metric} tone="brand">{metric}</Badge>)}
            </div>

            <h3 className="eval-subheading"><FileJson size={14} aria-hidden="true" /> Output shape</h3>
            <pre className="eval-output"><code>{layer.outputShape}</code></pre>
          </TabPanel>
        ))}
      </Card>
    </div>
  );
}
