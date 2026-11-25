import React from 'react'
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Check, Fingerprint, LockKeyhole, ShieldAlert, X } from 'lucide-react'
import { friendly } from '../format'

export default function ApprovalModal({ pending, onDecide, busy }) {
  const reduceMotion = useReducedMotion()

  return (
    <AnimatePresence>
      {pending && (
        <motion.div className="modal-scrim" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
          <motion.div
            className="modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="approval-title"
            aria-describedby="approval-lede"
            initial={reduceMotion ? false : { opacity: 0, scale: 0.96 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={reduceMotion ? { opacity: 0 } : { opacity: 0, scale: 0.97 }}
            transition={reduceMotion ? { duration: 0 } : { type: 'spring', stiffness: 320, damping: 28 }}
          >
            <span className="modal-rail" aria-hidden="true" />
            <div className="modal-fingerprint" aria-hidden="true">
              <Fingerprint size={86} strokeWidth={0.8} />
              <span className="modal-scan" />
            </div>

            <div className="modal-scroll">
              <div className="modal-top">
                <div className="modal-icon"><ShieldAlert size={25} strokeWidth={1.7} /></div>
                <div className="modal-ref">
                  <span>REQUEST</span>
                  <code>{pending.id}</code>
                </div>
              </div>

              <div className="eyebrow danger">HUMAN-IN-THE-LOOP CONTROL</div>
              <h2 className="modal-title" id="approval-title">Human approval required</h2>
              <p className="modal-lede" id="approval-lede">
                This action implies flight authorization. Nothing launches until you make an explicit decision.
              </p>

              <div className="modal-meta">
                <div>
                  <span className="meta-k"><Fingerprint size={12} /> ACTION</span>
                  <b>{friendly(pending.action, 'Authorization')}</b>
                </div>
                <div>
                  <span className="meta-k"><LockKeyhole size={12} /> APPROVAL ID</span>
                  <code>{pending.id}</code>
                </div>
              </div>

              <div className="modal-summary">
                <div className="eyebrow">REQUEST SUMMARY</div>
                <div className="summary-text markdown">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{pending.summary || 'No summary provided.'}</ReactMarkdown>
                </div>
              </div>
            </div>

            <div className="modal-footer">
              <div className="modal-actions">
                <motion.button className="btn btn-danger" disabled={busy} onClick={() => onDecide(pending.id, false)}
                  whileHover={reduceMotion ? undefined : { y: -2 }} whileTap={{ scale: 0.985 }}>
                  <X size={16} /> Reject
                </motion.button>
                <motion.button className="btn btn-primary" disabled={busy} onClick={() => onDecide(pending.id, true)}
                  whileHover={reduceMotion ? undefined : { y: -2 }} whileTap={{ scale: 0.985 }}>
                  <Check size={16} /> Approve
                </motion.button>
              </div>
              <div className="modal-foot">Fail-safe: any resume error rejects the authorization automatically.</div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
