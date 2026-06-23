import { useEffect, useState } from "react";
import CameraPanel from "./CameraPanel";
import { fetchCameras } from "../lib/api";

export default function MonitorView({ backendUrl, onToast }) {
  const [cameras, setCameras] = useState([]);
  const [hiddenCameraIds, setHiddenCameraIds] = useState([]);
  const [loading, setLoading] = useState(true);

  async function loadCameras() {
    setLoading(true);
    try {
      setCameras(await fetchCameras());
    } catch (error) {
      onToast(`Erro ao carregar cameras: ${error.message}`);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadCameras();
  }, []);

  const visibleCameras = cameras.filter((camera) => !hiddenCameraIds.includes(camera.id));

  function removePanel(cameraId) {
    if (visibleCameras.length === 1) {
      onToast("E necessario manter pelo menos um painel ativo.", "err");
      return;
    }
    setHiddenCameraIds((current) => [...current, cameraId]);
  }

  return (
    <div className="page-stack">
      <div className="hero-card">
        <div className="hero-grid">
          <div>
            <div className="eyebrow">Monitor de acesso</div>
            <h2 className="section-title">Cameras ativas</h2>
            <p className="section-sub">
              {visibleCameras.length === 1
                ? "1 painel de monitoramento ativo."
                : `${visibleCameras.length} paineis de monitoramento ativos.`}{" "}
              Cada painel usa a camera cadastrada e o respectivo portao USB.
            </p>
          </div>

          <div className="hero-note">
            <span className="section-sub" style={{ fontSize: 12 }}>
              As cameras exibidas aqui sao cadastradas na tela de Cameras. Para remover um painel desta visualizacao, clique em x no cabecalho dele.
            </span>
          </div>
        </div>
      </div>

      {loading ? <div className="empty">Carregando cameras...</div> : null}
      {!loading && !visibleCameras.length ? (
        <div className="empty">Nenhuma camera cadastrada para monitoramento.</div>
      ) : null}

      {!loading && visibleCameras.length ? (
        <div className="multi-monitor-grid" data-count={visibleCameras.length}>
          {visibleCameras.map((camera) => (
            <CameraPanel
              key={camera.id}
              camera={camera}
              panelName={camera.nome}
              gatePort={camera.porta_usb}
              backendUrl={backendUrl}
              onToast={onToast}
              onRemove={() => removePanel(camera.id)}
            />
          ))}
        </div>
      ) : null}
    </div>
  );
}
