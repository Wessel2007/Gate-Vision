import { useEffect, useRef, useState } from "react";
import {
  detectPlateFromBackend,
  lookupAuthorizedPlate,
  registerAccessDenied,
  registerAccessOpen,
  triggerGate
} from "../lib/api";
import { buildStatusIllustration, formatCPF, onlyPlate } from "../lib/utils";

function statusChip(detection, decision) {
  if (!detection) return <span className="chip warn">Aguardando identificacao</span>;
  if (decision === "liberado") return <span className="chip ok">Acesso liberado pelo porteiro</span>;
  if (decision === "negado") return <span className="chip err">Acesso negado pelo porteiro</span>;
  if (detection.status === "autorizado") return <span className="chip warn">Placa cadastrada (aguardando acao)</span>;
  return <span className="chip warn">Placa nao cadastrada (aguardando acao)</span>;
}

function statusImage(detection, decision) {
  if (!detection) return <div className="status-empty">Aguardando leitura da placa...</div>;
  if (decision === "liberado") return <img className="status-image" src={buildStatusIllustration("liberado")} alt="Status de acesso liberado" />;
  if (decision === "negado") return <img className="status-image" src={buildStatusIllustration("negado")} alt="Status de acesso negado" />;
  return <div className="status-empty">Placa identificada. Escolha liberar ou negar acesso.</div>;
}

export default function MonitorView({ backendUrl, onToast }) {
  const [detection, setDetection] = useState(null);
  const [decision, setDecision] = useState(null);
  const [manualPlate, setManualPlate] = useState("");
  const [previewUrl, setPreviewUrl] = useState("");
  const [webcamActive, setWebcamActive] = useState(false);
  const [processingLabel, setProcessingLabel] = useState("");
  const [cameraDevices, setCameraDevices] = useState([]);
  const [selectedCameraId, setSelectedCameraId] = useState("");

  const fileInputRef = useRef(null);
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const timerRef = useRef(null);
  const detectInFlightRef = useRef(false);
  const ocrInFlightRef = useRef(false);
  const lastProcessedPlateRef = useRef(null);

  useEffect(() => {
    if (videoRef.current && streamRef.current) {
      videoRef.current.srcObject = streamRef.current;
    }
  }, [webcamActive]);

  useEffect(() => {
    if (!navigator.mediaDevices?.enumerateDevices) return undefined;

    void loadCameraDevices();

    const handleDeviceChange = () => {
      void loadCameraDevices();
    };

    navigator.mediaDevices.addEventListener?.("devicechange", handleDeviceChange);
    return () => navigator.mediaDevices.removeEventListener?.("devicechange", handleDeviceChange);
  }, []);

  useEffect(() => () => {
    stopWebcam();
    if (previewUrl) URL.revokeObjectURL(previewUrl);
  }, [previewUrl]);

  async function loadCameraDevices(preferredId = null) {
    if (!navigator.mediaDevices?.enumerateDevices) return [];

    try {
      const devices = await navigator.mediaDevices.enumerateDevices();
      const cameras = devices
        .filter((device) => device.kind === "videoinput")
        .map((device, index) => ({
          id: device.deviceId,
          label: device.label || `Camera ${index + 1}`
        }));

      setCameraDevices(cameras);
      setSelectedCameraId((current) => {
        if (preferredId && cameras.some((camera) => camera.id === preferredId)) return preferredId;
        if (current && cameras.some((camera) => camera.id === current)) return current;
        return cameras[0]?.id || "";
      });

      return cameras;
    } catch (error) {
      console.warn("Falha ao listar cameras:", error);
      return [];
    }
  }

  function resetProcessedPlate() {
    lastProcessedPlateRef.current = null;
  }

  async function openGate(detected, autoTriggered = false) {
    if (!detected) return;
    await registerAccessOpen(detected.placa);
    setDecision("liberado");
    onToast(autoTriggered ? "Placa autorizada. Portao aberto automaticamente." : "Portao aberto pelo porteiro.", "ok");
    try {
      await triggerGate(backendUrl);
    } catch (error) {
      console.warn("open-gate indisponivel:", error);
    }
  }

  async function processPlate(plate, autoOpen = true) {
    const clean = onlyPlate(plate);
    if (clean.length < 7 || detectInFlightRef.current) return;
    if (lastProcessedPlateRef.current === clean && detection?.placa === clean) return;

    detectInFlightRef.current = true;
    lastProcessedPlateRef.current = clean;
    setDecision(null);
    setProcessingLabel("Validando...");

    try {
      const nextDetection = await lookupAuthorizedPlate(clean);
      setDetection(nextDetection);
      if (autoOpen && nextDetection.status === "autorizado") {
        await openGate(nextDetection, true);
      }
    } catch (error) {
      setDetection({ placa: clean, status: "nao-cadastrado", morador: null });
      onToast(`Erro ao verificar placa: ${error.message}`);
    } finally {
      setProcessingLabel("");
      detectInFlightRef.current = false;
    }
  }

  async function processImage(file, fromWebcam = false) {
    if (ocrInFlightRef.current) return;
    ocrInFlightRef.current = true;
    if (!fromWebcam) {
      setDetection(null);
      setDecision(null);
    }
    setProcessingLabel("Detectando...");

    try {
      const result = await detectPlateFromBackend(backendUrl, file);
      if (!result.placa) {
        if (!fromWebcam) {
          setDetection({ placa: "---", status: "nao-detectado", morador: null });
          onToast("Nenhuma placa detectada na imagem.");
        }
        return;
      }

      const clean = onlyPlate(result.placa);
      setManualPlate(clean);
      if (fromWebcam) stopWebcam();
      await processPlate(clean, true);
    } catch (error) {
      if (!fromWebcam) {
        onToast(`Erro ao processar imagem: ${error.message}`);
      }
    } finally {
      setProcessingLabel("");
      ocrInFlightRef.current = false;
    }
  }

  async function startWebcam(cameraId = selectedCameraId) {
    if (!navigator.mediaDevices?.getUserMedia) {
      onToast("Seu navegador nao suporta acesso a webcam.");
      return;
    }

    try {
      let stream = null;
      let selectedCameraUnavailable = false;

      if (cameraId) {
        try {
          stream = await navigator.mediaDevices.getUserMedia({ video: { deviceId: { exact: cameraId } } });
        } catch (error) {
          if (error.name === "OverconstrainedError" || error.name === "NotReadableError") {
            selectedCameraUnavailable = true;
          } else {
            throw error;
          }
        }
      }

      if (!stream && cameraId) {
        try {
          stream = await navigator.mediaDevices.getUserMedia({ video: { deviceId: { ideal: cameraId } } });
        } catch (error) {
          if (error.name !== "OverconstrainedError" && error.name !== "NotReadableError") {
            throw error;
          }
        }
      }

      if (!stream) {
        stream = await navigator.mediaDevices.getUserMedia({ video: true });
      }

      const activeTrack = stream.getVideoTracks()[0];
      const activeCameraId = activeTrack?.getSettings?.().deviceId || cameraId || "";

      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
      }
      streamRef.current = stream;
      setWebcamActive(true);
      setPreviewUrl("");
      if (activeCameraId) setSelectedCameraId(activeCameraId);
      await loadCameraDevices(activeCameraId);

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }

      if (selectedCameraUnavailable && activeCameraId && cameraId && activeCameraId !== cameraId) {
        onToast("A camera USB selecionada nao abriu. O navegador usou outra camera disponivel.");
      }

      if (timerRef.current) clearInterval(timerRef.current);
      timerRef.current = window.setInterval(() => {
        if (!detectInFlightRef.current && !ocrInFlightRef.current) {
          void captureAndDetect(true);
        }
      }, 3000);
    } catch (error) {
      const message = error.name === "NotAllowedError"
        ? "Permissao de camera negada. Permita o acesso no navegador."
        : error.name === "NotFoundError"
          ? "Nenhuma camera encontrada no dispositivo."
          : error.name === "OverconstrainedError"
            ? "A camera selecionada nao esta disponivel no momento."
          : `Erro ao acessar a webcam: ${error.message}`;
      onToast(message);
    }
  }

  function stopWebcam() {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setWebcamActive(false);
  }

  async function captureAndDetect(silent = false) {
    if (!videoRef.current || !streamRef.current) {
      if (!silent) onToast("Webcam nao esta ativa.");
      return;
    }
    if (detectInFlightRef.current || ocrInFlightRef.current) return;

    const canvas = document.createElement("canvas");
    canvas.width = videoRef.current.videoWidth || 640;
    canvas.height = videoRef.current.videoHeight || 480;
    canvas.getContext("2d").drawImage(videoRef.current, 0, 0, canvas.width, canvas.height);

    const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.92));
    if (!blob) {
      onToast("Erro ao capturar frame da webcam.");
      return;
    }

    const file = new File([blob], "webcam_frame.jpg", { type: "image/jpeg" });
    await processImage(file, true);
  }

  async function handleManualOpen() {
    if (!detection) return;
    try {
      await openGate(detection, false);
    } catch (error) {
      onToast(`Erro ao registrar abertura: ${error.message}`);
    }
  }

  async function handleDeny() {
    if (!detection) return;
    try {
      await registerAccessDenied(detection.placa);
      setDecision("negado");
      onToast("Acesso negado registrado.", "ok");
    } catch (error) {
      onToast(`Erro ao registrar negacao: ${error.message}`);
    }
  }

  async function handleManualInputChange(event) {
    const clean = onlyPlate(event.target.value);
    setManualPlate(clean);
    if (clean.length < 7) {
      resetProcessedPlate();
      return;
    }
    await processPlate(clean, true);
  }

  async function handleFileChange(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl(URL.createObjectURL(file));
    await processImage(file, false);
  }

  async function handleCameraChange(event) {
    const nextCameraId = event.target.value;
    setSelectedCameraId(nextCameraId);
    if (!webcamActive) return;

    stopWebcam();
    await startWebcam(nextCameraId);
  }

  const currentChip = statusChip(detection, decision);
  const currentImage = statusImage(detection, decision);

  return (
    <div className="page-stack">
      <div className="hero-card">
        <div className="hero-grid">
          <div>
            <div className="eyebrow">Monitor de leitura</div>
            <h2 className="section-title">Triagem de veiculos na entrada principal</h2>
            <p className="section-sub">Envie imagem, use a webcam ou digite a placa manualmente para validar a autorizacao e decidir a abertura do portao.</p>
            <div className="hero-meta">{currentChip}</div>
          </div>
          <div className="hero-note">
            <div>
              <div className="eyebrow">Ultima placa</div>
              <strong className="mono">{detection ? detection.placa : "---"}</strong>
            </div>
            <p className="section-sub">{detection?.morador ? detection.morador.nome : "Aguardando identificacao para exibir dados do morador."}</p>
          </div>
        </div>
      </div>

      <div className="monitor-layout">
        <div className="monitor-tools">
          <div className="card">
            <div className="card-head">Captura e leitura</div>
            <div className="card-body">
              <div className="camera">
                {previewUrl && !webcamActive ? (
                  <div style={{ width: "100%", height: "100%", overflow: "hidden" }}>
                    <img src={previewUrl} style={{ width: "100%", height: "100%", objectFit: "contain" }} />
                  </div>
                ) : null}
                <video ref={videoRef} className="webcam-video" style={{ display: webcamActive ? "block" : "none" }} autoPlay playsInline muted />
                {!previewUrl && !webcamActive ? <div>Envie uma foto, use a webcam<br />ou digite a placa manualmente</div> : null}
              </div>

              <div className="monitor-toolbar" style={{ marginTop: 12 }}>
                <input className="input mono" value={manualPlate} onChange={handleManualInputChange} placeholder="Ex: BRA2E24" maxLength={7} />
              </div>

              <div className="monitor-toolbar" style={{ marginTop: 10 }}>
                <select className="input" value={selectedCameraId} onChange={handleCameraChange} disabled={!cameraDevices.length}>
                  <option value="">{cameraDevices.length ? "Selecione uma camera" : "Nenhuma camera encontrada"}</option>
                  {cameraDevices.map((camera) => (
                    <option key={camera.id} value={camera.id}>{camera.label}</option>
                  ))}
                </select>
              </div>

              <div className="monitor-toolbar" style={{ marginTop: 10 }}>
                <input ref={fileInputRef} type="file" accept="image/*" style={{ display: "none" }} onChange={handleFileChange} />
                <button className="btn" onClick={() => fileInputRef.current?.click()} type="button">Enviar foto</button>
              </div>

              <div className="monitor-toolbar" style={{ marginTop: 10 }}>
                <button className="btn" onClick={startWebcam} type="button" disabled={webcamActive}>Usar webcam</button>
                <button className="btn err" onClick={stopWebcam} type="button" style={{ display: webcamActive ? "" : "none" }}>Parar webcam</button>
              </div>

              {processingLabel ? <div className="empty" style={{ marginTop: 12 }}>{processingLabel}</div> : null}
            </div>
          </div>

          <div className="monitor-banner">
            <strong>Fluxo recomendado</strong>
            <p className="section-sub">A validacao acontece automaticamente quando a placa e reconhecida. Se estiver autorizada, o portao e aberto sem confirmacao manual.</p>
          </div>
        </div>

        <div className="monitor-result">
          <div className="card">
            <div className="card-head">Resultado da leitura</div>
            <div className="card-body">
              <div className="status-image-wrap">{currentImage}</div>
              <div style={{ marginBottom: 12 }}>{currentChip}</div>
              <div className="status-box">
                <div className="row"><span>Placa</span><strong className="mono">{detection ? detection.placa : "---"}</strong></div>
                <div className="row"><span>Morador</span><strong>{detection?.morador ? detection.morador.nome : "-"}</strong></div>
                <div className="row"><span>CPF</span><strong>{detection?.morador ? formatCPF(detection.morador.cpf) : "-"}</strong></div>
                <div className="row"><span>Apartamento</span><strong>{detection?.morador ? `${detection.morador.apartamento} - Torre ${detection.morador.torre}` : "-"}</strong></div>
              </div>
              <div className="actions" style={{ marginTop: 12 }}>
                <button className="btn ok" onClick={handleManualOpen} type="button" disabled={!detection || !!decision}>Abrir portao</button>
                <button className="btn err" onClick={handleDeny} type="button" disabled={!detection || !!decision}>Negar acesso</button>
              </div>
            </div>
          </div>

          <div className="split-card">
            <div className="metric-mini">
              <span>Status atual</span>
              <strong>{decision ? decision.toUpperCase() : "EM ANALISE"}</strong>
            </div>
            <div className="metric-mini">
              <span>Origem</span>
              <strong>{detection ? "PLACA DETECTADA" : "AGUARDANDO"}</strong>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
