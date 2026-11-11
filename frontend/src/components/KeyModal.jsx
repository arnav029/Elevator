import { useState } from 'react'
import { label, urlFor } from '../constants'

function CopyRow({ text }) {
  const [copied, setCopied] = useState(false)
  return (
    <div className="copy-row">
      <input readOnly value={text} onFocus={(e) => e.target.select()} />
      <button className="btn" onClick={async () => {
        try { await navigator.clipboard.writeText(text); setCopied(true) } catch { /* ignore */ }
      }}>{copied ? 'copied' : 'copy'}</button>
    </div>
  )
}

export default function KeyModal({ n, ownerKey, basement, onClose }) {
  const editUrl = `${location.origin}${urlFor(n)}/edit#key=${ownerKey}`
  const shareUrl = `${location.origin}${urlFor(n)}`
  return (
    <div className="modal-back">
      <div className="modal key-modal">
        <h2>Welcome home. Floor {label(n)} is yours.</h2>
        <p><b>Save this edit link.</b> It's the only key to your room. There are no accounts, so if you lose it, nobody can let you back in.</p>
        <CopyRow text={editUrl} />
        <p>Share your floor:</p>
        <CopyRow text={shareUrl} />
        {!basement && <img className="preview-img" src={`/api/floors/${n}/preview.png?v=${Date.now()}`} alt={`Preview of floor ${label(n)}`} />}
        <p className="muted">Come back to see who visited and read the notes they left. Rooms nobody visits for 30 days gather cobwebs, and after 90 quiet days with no sign of you, the floor goes back on the market.</p>
        <div className="modal-actions">
          <button className="btn claim" onClick={onClose}>I saved it</button>
        </div>
      </div>
    </div>
  )
}
