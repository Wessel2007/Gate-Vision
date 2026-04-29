export default function ToastViewport({ toasts }) {
  return (
    <>
      {toasts.map((toast, index) => (
        <div
          key={toast.id}
          className={toast.type === "ok" ? "chip ok" : "error"}
          style={{
            position: "fixed",
            bottom: 24 + index * 62,
            right: 24,
            zIndex: 9999,
            padding: "12px 20px",
            borderRadius: 8,
            maxWidth: 420,
            fontSize: 14,
            boxShadow: "0 4px 16px rgba(0,0,0,.25)"
          }}
        >
          {toast.message}
        </div>
      ))}
    </>
  );
}
