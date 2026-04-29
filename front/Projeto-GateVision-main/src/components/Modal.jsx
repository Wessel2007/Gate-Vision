export default function Modal({ open, title, onClose, children }) {
  if (!open) return null;

  return (
    <div className="modal-shell">
      <div className="modal-backdrop" onClick={onClose} role="presentation" />
      <div className="modal-card" role="dialog" aria-modal="true" aria-labelledby="modalTitle">
        <div className="modal-head">
          <strong id="modalTitle">{title}</strong>
          <button className="btn" onClick={onClose} type="button">Fechar</button>
        </div>
        <div className="modal-body">{children}</div>
      </div>
    </div>
  );
}
