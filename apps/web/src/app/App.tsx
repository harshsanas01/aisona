import { Navigate, Route, Routes } from 'react-router-dom';
import { AppShell } from '../components/layout/AppShell';
import { AskPage } from '../features/ask-question/AskPage';
import { CallsPage } from '../features/calls/CallsPage';
import { SafetyEventsPage } from '../features/safety/SafetyEventsPage';
import { IngestionPage } from '../features/ingestion/IngestionPage';
import { EvaluationsPage } from '../features/evaluations/EvaluationsPage';
import { PatientsPage, PatientProfilePage } from '../features/patients';
import { ActionCenterPage } from '../features/tasks';
import { BriefsPage } from '../features/briefs';
import { RetrievalLabPage } from '../features/retrieval-lab/RetrievalLabPage';

function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<Navigate to="/ask" replace />} />
        <Route path="/ask" element={<AskPage />} />
        <Route path="/calls" element={<CallsPage />} />
        <Route path="/patients" element={<PatientsPage />} />
        <Route path="/patients/:patientId" element={<PatientProfilePage />} />
        <Route path="/action-center" element={<ActionCenterPage />} />
        <Route path="/briefs" element={<BriefsPage />} />
        <Route path="/safety-events" element={<SafetyEventsPage />} />
        <Route path="/ingestion" element={<IngestionPage />} />
        <Route path="/evaluations" element={<EvaluationsPage />} />
        <Route path="/retrieval-lab" element={<RetrievalLabPage />} />
        <Route path="*" element={<Navigate to="/ask" replace />} />
      </Route>
    </Routes>
  );
}

export default App;
