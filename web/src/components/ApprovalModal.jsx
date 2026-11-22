import React from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { ShieldAlert, Check, X, LockKeyhole, Fingerprint } from 'lucide-react'
import { friendly } from '../format'

export default function ApprovalModal({ pending, onDecide, busy }) {
  return (
    <AnimatePresence>
      {pending && (
        <motion.div className="modal-scrim" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
          <motion.div
            className="modal"
            role="dialog" aria-modal="true" aria-label="Human approval required"
            initial={{ opacity: 0, y: 36, scale: 0.94 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 18, scale: 0.96 }}
            transition={{ type: 'spring', stiffness: 320, damping: 28 }}
          >
            <div className="modal-glow" />
            <div className="modal-icon"><ShieldAlert size={26} strokeWidth={1.7} /></div>
            <div className="eyebrow danger">HUMAN-IN-THE-LOOP CONTROL</div>
            <h2 className="modal-title">Human approval required</h2>
            <p className="modal-lede">This action implies flight authorization. Nothing launches until you make an explicit decision.</p>

            <div className="modal-meta">
              <div><span className="meta-k"><Fingerprint size={13} /> ACTION</span><b>{friendly(pending.action, 'Authorization')}</b></div>
              <div><span className="meta-k"><LockKeyhole size={13} /> APPROVAL ID</span><code>{pending.id}</code></div>
            </div>

            <div className="modal-summary">
              <div className="eyebrow">REQUEST SUMMARY</div>
              <div className="summary-text markdown"><ReactMarkdown remarkPlugins={[remarkGfm]}>{pending.summary || 'No summary provided.'}</ReactMarkdown></div>
            </div>

            <div className="modal-actions">
              <motion.button className="btn btn-danger" disabled={busy} onClick={() => onDecide(false)} whileHover={{ y: -2 }} whileTap={{ scale: 0.98 }}>
                <X size={16} /> Reject
              </motion.button>
              <motion.button className="btn btn-primary" disabled={busy} onClick={() => onDecide(true)} whileHover={{ y: -2 }} whileTap={{ scale: 0.98 }}>
                <Check size={16} /> Approve
              </motion.button>
            </div>
            <div className="modal-foot">Fail-safe: any resume error rejects the authorization automatically.</div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
