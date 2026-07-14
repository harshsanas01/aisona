import { useEffect, useMemo, useRef, useState } from 'react';
import { Calendar, ChevronDown, ChevronUp, Clock, Headset, Phone, User, X } from 'lucide-react';
import { Drawer } from '../../components/ui/Drawer';
import { IconButton } from '../../components/ui/IconButton';
import { Badge } from '../../components/ui/Badge';
import { Skeleton } from '../../components/ui/Skeleton';
import { ErrorState } from '../../components/ui/ErrorState';
import { SafetyBadge } from '../../components/ui/SafetyBadge';
import { safetyCategoryMeta } from '../safety/safetyCategories';
import { useTranscriptDrawer } from './TranscriptDrawerContext';
import type { SafetyEvent } from '../../types';
import './transcript-drawer.css';

function prefersReducedMotion(): boolean {
  return typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

function formatDuration(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  const rest = seconds % 60;
  return `${minutes}m ${rest.toString().padStart(2, '0')}s`;
}

export function TranscriptDrawer() {
  const { target, transcript, safetyEvents, loading, error, close } = useTranscriptDrawer();
  const [activeCategory, setActiveCategory] = useState<string | null>(null);
  const turnRefs = useRef<Map<number, HTMLDivElement>>(new Map());
  const [flagIndex, setFlagIndex] = useState(0);

  useEffect(() => {
    setActiveCategory(target?.category ?? null);
    setFlagIndex(0);
  }, [target?.callId]);

  const eventsByTurn = useMemo(() => {
    const map = new Map<number, SafetyEvent[]>();
    for (const event of safetyEvents) {
      if (activeCategory && event.category !== activeCategory) continue;
      const list = map.get(event.turn_number) ?? [];
      list.push(event);
      map.set(event.turn_number, list);
    }
    return map;
  }, [safetyEvents, activeCategory]);

  const citationTurns = useMemo(() => {
    if (!target?.turnStart || !target.turnEnd) return new Set<number>();
    const set = new Set<number>();
    for (let turn = target.turnStart; turn <= target.turnEnd; turn++) set.add(turn);
    return set;
  }, [target?.turnStart, target?.turnEnd]);

  const flaggedTurns = useMemo(() => {
    const set = new Set<number>([...citationTurns, ...eventsByTurn.keys()]);
    return Array.from(set).sort((a, b) => a - b);
  }, [citationTurns, eventsByTurn]);

  const categories = useMemo(() => Array.from(new Set(safetyEvents.map((event) => event.category))), [safetyEvents]);

  const scrollToTurn = (turnNumber: number, behavior: ScrollBehavior = 'smooth') => {
    turnRefs.current.get(turnNumber)?.scrollIntoView({ behavior, block: 'center' });
  };

  useEffect(() => {
    if (!transcript || flaggedTurns.length === 0) return;
    const start = target?.focusTurn ?? target?.turnStart ?? flaggedTurns[0];
    const startIndex = Math.max(0, flaggedTurns.indexOf(start));
    setFlagIndex(startIndex === -1 ? 0 : startIndex);
    const timer = window.setTimeout(() => {
      scrollToTurn(flaggedTurns[startIndex === -1 ? 0 : startIndex], prefersReducedMotion() ? 'auto' : 'smooth');
    }, 60);
    return () => window.clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [transcript]);

  const goToFlag = (direction: 1 | -1) => {
    if (flaggedTurns.length === 0) return;
    const nextIndex = (flagIndex + direction + flaggedTurns.length) % flaggedTurns.length;
    setFlagIndex(nextIndex);
    scrollToTurn(flaggedTurns[nextIndex]);
  };

  if (!target) return null;

  return (
    <Drawer open={Boolean(target)} onClose={close} labelledBy="transcript-drawer-title">
      <div className="transcript-drawer-header">
        <div className="transcript-drawer-heading">
          <h2 id="transcript-drawer-title">
            {transcript ? transcript.patient.name : 'Loading transcript…'}
          </h2>
          {transcript ? (
            <div className="transcript-meta-row">
              <span><Calendar size={13} aria-hidden="true" /> {transcript.date}</span>
              <span><Clock size={13} aria-hidden="true" /> {formatDuration(transcript.duration_seconds)}</span>
              <span className="transcript-meta-mono"><Phone size={13} aria-hidden="true" /> {transcript.call_id}</span>
              <span>Age {transcript.patient.age}</span>
            </div>
          ) : null}
        </div>
        <IconButton icon={<X size={18} />} label="Close transcript" tooltipPlacement="bottom" onClick={close} />
      </div>

      {flaggedTurns.length > 0 ? (
        <div className="transcript-nav-row">
          <span className="transcript-nav-count" aria-live="polite">
            {flagIndex + 1} of {flaggedTurns.length} highlighted turns
          </span>
          <div className="transcript-nav-buttons">
            <IconButton icon={<ChevronUp size={16} />} label="Previous highlighted turn" size="sm" onClick={() => goToFlag(-1)} showTooltip={false} />
            <IconButton icon={<ChevronDown size={16} />} label="Next highlighted turn" size="sm" onClick={() => goToFlag(1)} showTooltip={false} />
          </div>
        </div>
      ) : null}

      {categories.length > 0 ? (
        <div className="transcript-legend">
          <button
            type="button"
            className={`filter-chip ${activeCategory === null ? 'active' : ''}`}
            onClick={() => setActiveCategory(null)}
          >
            All flags
          </button>
          {categories.map((category) => {
            const meta = safetyCategoryMeta(category);
            const Icon = meta.icon;
            return (
              <button
                key={category}
                type="button"
                className={`filter-chip ${activeCategory === category ? 'active' : ''}`}
                onClick={() => setActiveCategory(activeCategory === category ? null : category)}
              >
                <Icon size={12} aria-hidden="true" /> {meta.label}
              </button>
            );
          })}
        </div>
      ) : null}

      <div className="transcript-body">
        {loading ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <Skeleton variant="card" count={4} />
          </div>
        ) : error ? (
          <ErrorState message={error} />
        ) : transcript ? (
          <div className="turn-list">
            {transcript.turns.map((turn) => {
              const isCited = citationTurns.has(turn.turn_number);
              const turnEvents = eventsByTurn.get(turn.turn_number) ?? [];
              const isAssistant = turn.speaker === 'assistant';
              return (
                <div
                  key={turn.turn_number}
                  ref={(node) => {
                    if (node) turnRefs.current.set(turn.turn_number, node);
                    else turnRefs.current.delete(turn.turn_number);
                  }}
                  id={`turn-${turn.turn_number}`}
                  className={`turn ${isAssistant ? 'turn-assistant' : 'turn-participant'} ${isCited ? 'turn-cited' : ''} ${turnEvents.length ? 'turn-flagged' : ''}`}
                >
                  <div className="turn-avatar" aria-hidden="true">
                    {isAssistant ? <Headset size={15} /> : <User size={15} />}
                  </div>
                  <div className="turn-content">
                    <div className="turn-top">
                      <strong>{isAssistant ? 'Care team' : transcript.patient.name}</strong>
                      <span className="turn-number">Turn {turn.turn_number}</span>
                      {isCited ? <Badge tone="brand">Cited</Badge> : null}
                    </div>
                    <p>{turn.text}</p>
                    {turnEvents.length ? (
                      <div className="safety-badges">
                        {turnEvents.map((event, index) => (
                          <SafetyBadge
                            key={`${event.category}-${index}`}
                            category={event.category}
                            severity={event.severity}
                            title={event.explanation}
                          />
                        ))}
                      </div>
                    ) : null}
                  </div>
                </div>
              );
            })}
          </div>
        ) : null}
      </div>
    </Drawer>
  );
}
