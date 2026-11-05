import React from 'react';
import { usePreferences } from '../../../context/PreferencesContext';
import { Check, Lock, ShieldCheck } from 'lucide-react';
import common from './CategoryCommon.module.css';

export default function PersonalizationCategory() {
  const { preferences, updatePreference, saveStatus } = usePreferences();

  return (
    <div className={common.container}>
      <div className={common.header}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <h2 className={common.title}>AI &amp; Research Personalization</h2>
            <p className={common.description}>
              Customize the depth, tone, and formatting of AI answers while preserving strict transcript grounding.
            </p>
          </div>
          {saveStatus === 'saved' && (
            <span className={common.saveIndicator}>
              <Check size={14} /> Saved
            </span>
          )}
        </div>
      </div>

      {/* Mandatory Transcript Grounding Notice */}
      <div className={common.noticeBox}>
        <ShieldCheck size={18} className={common.noticeIcon} />
        <div>
          <strong style={{ color: '#ffffff', display: 'block', marginBottom: '2px' }}>
            Transcript Grounding is Permanently Enforced
          </strong>
          <span>
            Every answer is strictly constrained to the video transcript. Style and length preferences adjust organization and tone, but never allow outside knowledge or unverified speculation.
          </span>
        </div>
      </div>

      {/* Response Depth & Tone */}
      <div className={common.section}>
        <div>
          <h3 className={common.sectionTitle}>Response Style &amp; Length</h3>
          <p className={common.sectionSubtitle}>
            These preferences are passed directly to the Groq LLM prompt on every research inquiry.
          </p>
        </div>

        <div className={common.row}>
          <div className={common.rowInfo}>
            <label htmlFor="answerLengthSelect" className={common.rowLabel}>
              Answer Length
            </label>
            <span className={common.rowDescription}>
              Select the default volume of detail provided in AI answers.
            </span>
          </div>
          <select
            id="answerLengthSelect"
            className={common.select}
            value={preferences.answerLength}
            onChange={(e) => updatePreference('answerLength', e.target.value)}
            data-testid="settings-answer-length-select"
          >
            <option value="concise">Concise (1–2 short paragraphs / key points)</option>
            <option value="balanced">Balanced (Standard comprehensive response)</option>
            <option value="detailed">Detailed (In-depth analysis of transcript context)</option>
          </select>
        </div>

        <div className={common.row}>
          <div className={common.rowInfo}>
            <label htmlFor="responseStyleSelect" className={common.rowLabel}>
              Response Tone &amp; Style
            </label>
            <span className={common.rowDescription}>
              Define the tone and vocabulary used by the research assistant.
            </span>
          </div>
          <select
            id="responseStyleSelect"
            className={common.select}
            value={preferences.responseStyle}
            onChange={(e) => updatePreference('responseStyle', e.target.value)}
            data-testid="settings-response-style-select"
          >
            <option value="simple">Simple (Plain, accessible, jargon-free explanations)</option>
            <option value="explanatory">Explanatory (Step-by-step conceptual walkthroughs)</option>
            <option value="technical">Technical (Rigorous precision with code/domain terms)</option>
          </select>
        </div>
      </div>

      {/* Formatting & Citation Preferences */}
      <div className={common.section}>
        <div>
          <h3 className={common.sectionTitle}>Formatting &amp; Evidence</h3>
          <p className={common.sectionSubtitle}>
            Control how sources, lists, and examples are organized in assistant responses.
          </p>
        </div>

        <div className={common.row}>
          <div className={common.rowInfo}>
            <span className={common.rowLabel}>Prefer Structured Answers</span>
            <span className={common.rowDescription}>
              Organize answers using markdown headers, bullet lists, and clear hierarchy.
            </span>
          </div>
          <label className={common.switch} aria-label="Prefer structured answers">
            <input
              type="checkbox"
              checked={preferences.preferStructured}
              onChange={(e) => updatePreference('preferStructured', e.target.checked)}
              data-testid="settings-prefer-structured-switch"
            />
            <span className={common.slider} />
          </label>
        </div>

        <div className={common.row}>
          <div className={common.rowInfo}>
            <span className={common.rowLabel}>Include Transcript Examples</span>
            <span className={common.rowDescription}>
              Highlight concrete code snippets and case studies when explicitly mentioned in the transcript.
            </span>
          </div>
          <label className={common.switch} aria-label="Include transcript examples">
            <input
              type="checkbox"
              checked={preferences.includeExamples}
              onChange={(e) => updatePreference('includeExamples', e.target.checked)}
              data-testid="settings-include-examples-switch"
            />
            <span className={common.slider} />
          </label>
        </div>

        <div className={common.row}>
          <div className={common.rowInfo}>
            <span className={common.rowLabel}>Display Timestamp Citations</span>
            <span className={common.rowDescription}>
              Show interactive, clickable timestamp chips underneath answers to jump to video evidence.
            </span>
          </div>
          <label className={common.switch} aria-label="Display timestamp citations">
            <input
              type="checkbox"
              checked={preferences.showCitations}
              onChange={(e) => updatePreference('showCitations', e.target.checked)}
              data-testid="settings-show-citations-switch"
            />
            <span className={common.slider} />
          </label>
        </div>

        <div className={common.row}>
          <div className={common.rowInfo}>
            <span className={common.rowLabel}>Strict Transcript Grounding</span>
            <span className={common.rowDescription}>
              Ensures hallucinated outside facts are strictly prohibited. Required by YtGenius core architecture.
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span className={`${common.badge} ${common.badgeSuccess}`}>
              <Lock size={11} /> Locked &amp; Active
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
