import React from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { motion } from 'framer-motion'
import { friendly, severityClass } from '../format'

export function Markdown({ children }) {
  return (
    <div className="markdown">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{children || ''}</ReactMarkdown>
    </div>
  )
}

export function SeverityPill({ value }) {
  const label = friendly(value, '—')
  return <span className={`pill pill-${severityClass(value)}`}>{label}</span>
}

export function StatusDot({ tone = 'green', pulse = false, title }) {
  return <span className={`dot dot-${tone} ${pulse ? 'dot-pulse' : ''}`} title={title} />
}

export function Spinner({ size = 16 }) {
  return <span className="spinner" style={{ width: size, height: size }} aria-hidden="true" />
}

export function Toasts({ items }) {
  return (
    <div className="toast-stack" aria-live="polite">
      {items.map(t => (
        <motion.div
          key={t.id}
          className={`toast toast-${t.tone || 'info'}`}
          initial={{ opacity: 0, y: 14, scale: 0.96 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 8, scale: 0.97 }}
          transition={{ type: 'spring', stiffness: 380, damping: 30 }}
        >
          <span className="toast-mark">{t.tone === 'danger' ? '!' : '✓'}</span>
          {t.text}
        </motion.div>
      ))}
    </div>
  )
}

export function EmptyRow({ icon: Icon, title, hint }) {
  return (
    <div className="empty-row">
      {Icon && <div className="empty-row-icon"><Icon size={22} strokeWidth={1.6} /></div>}
      <div>
        <div className="empty-row-title">{title}</div>
        {hint && <div className="empty-row-hint">{hint}</div>}
      </div>
    </div>
  )
}

export function SectionHead({ eyebrow, title, hint, right }) {
  return (
    <div className="section-head">
      <div>
        {eyebrow && <div className="eyebrow">{eyebrow}</div>}
        <h1 className="section-title">{title}</h1>
        {hint && <p className="section-hint">{hint}</p>}
      </div>
      {right}
    </div>
  )
}
