import { useEffect, useState } from "react";
import Modal from "./Modal";
import { deleteCamera, fetchCameras, fetchSerialPorts, saveCamera, updateCamera } from "../lib/api";

function CameraForm({ backendUrl, initialData, loading, onSubmit, onClose, onToast }) {
  const [form, setForm] = useState({ nome: "", localizacao: "", tipo_camera_id: "1", porta_usb: "" });
  const [ports, setPorts] = useState([]);
  const [loadingPorts, setLoadingPorts] = useState(false);

  useEffect(() => {
    setForm({
      nome: initialData?.nome || "",
      localizacao: initialData?.localizacao || "",
      tipo_camera_id: initialData?.tipo_camera_id || "1",
      porta_usb: initialData?.porta_usb || ""
    });
  }, [initialData]);

  function update(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function loadPorts() {
    setLoadingPorts(true);
    try {
      const nextPorts = await fetchSerialPorts(backendUrl);
      setPorts(nextPorts);
      setForm((current) => {
        if (current.porta_usb && nextPorts.some((port) => port.device === current.porta_usb)) return current;
        return { ...current, porta_usb: nextPorts[0]?.device || current.porta_usb || "" };
      });
    } catch (error) {
      setPorts([]);
      onToast(`Erro ao listar portas USB: ${error.message}`);
    } finally {
      setLoadingPorts(false);
    }
  }

  useEffect(() => {
    void loadPorts();
  }, [backendUrl]);

  const selectedPortConnected = ports.some((port) => port.device === form.porta_usb);

  return (
    <form className="form-grid" onSubmit={(event) => { event.preventDefault(); onSubmit(form); }}>
      <div>
        <label className="login-sub">Nome da camera</label>
        <input required className="input" placeholder="Ex: CAM-PORT-01" value={form.nome} onChange={(event) => update("nome", event.target.value)} />
      </div>
      <div>
        <label className="login-sub">Localizacao</label>
        <input required className="input" placeholder="Ex: Portaria Principal" value={form.localizacao} onChange={(event) => update("localizacao", event.target.value)} />
      </div>
      <div>
        <label className="login-sub">Porta USB do portao</label>
        <div style={{ display: "flex", gap: 8 }}>
          <select
            required
            className="input mono"
            value={form.porta_usb}
            onChange={(event) => update("porta_usb", event.target.value)}
            disabled={loadingPorts || (!ports.length && !form.porta_usb)}
          >
            <option value="">{loadingPorts ? "Buscando portas..." : "Nenhuma porta USB encontrada"}</option>
            {form.porta_usb && !selectedPortConnected ? (
              <option value={form.porta_usb}>{form.porta_usb} (nao conectada)</option>
            ) : null}
            {ports.map((port) => (
              <option key={port.device} value={port.device}>
                {port.device} - {port.description}
              </option>
            ))}
          </select>
          <button className="btn" type="button" onClick={loadPorts} disabled={loadingPorts}>
            Atualizar
          </button>
        </div>
      </div>
      <div>
        <label className="login-sub">Tipo</label>
        <select className="input" value={form.tipo_camera_id} onChange={(event) => update("tipo_camera_id", event.target.value)}>
          <option value="1">Entrada</option>
          <option value="2">Saida</option>
          <option value="3">Garagem</option>
          <option value="4">Estacionamento</option>
        </select>
      </div>
      <div className="form-actions modal-actions">
        <button className="btn primary" type="submit" disabled={loading}>{loading ? "Salvando..." : "Salvar camera"}</button>
        <button className="btn" onClick={onClose} type="button">Cancelar</button>
      </div>
    </form>
  );
}

export default function CamerasView({ backendUrl, onToast }) {
  const [cameras, setCameras] = useState([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [editingCamera, setEditingCamera] = useState(null);

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

  async function handleSave(form) {
    setSaving(true);
    try {
      if (editingCamera) {
        await updateCamera(editingCamera.id, form);
        onToast("Camera atualizada com sucesso!", "ok");
      } else {
        await saveCamera(form);
        onToast("Camera salva com sucesso!", "ok");
      }
      setOpen(false);
      setEditingCamera(null);
      await loadCameras();
    } catch (error) {
      onToast(`Erro ao salvar camera: ${error.message}`);
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(cameraId) {
    if (!window.confirm("Deseja remover esta camera?")) return;
    try {
      await deleteCamera(cameraId);
      onToast("Camera removida.", "ok");
      await loadCameras();
    } catch (error) {
      onToast(`Erro ao remover camera: ${error.message}`);
    }
  }

  function handleOpenCreate() {
    setEditingCamera(null);
    setOpen(true);
  }

  function handleOpenEdit(camera) {
    setEditingCamera(camera);
    setOpen(true);
  }

  function handleCloseModal() {
    setOpen(false);
    setEditingCamera(null);
  }

  return (
    <div className="page-stack">
      <div className="panel-header">
        <div>
          <div className="eyebrow">Infraestrutura</div>
          <h2 className="section-title">Cameras do sistema</h2>
          <p className="section-sub">Cadastre os pontos de captura e organize os equipamentos de entrada, saida e garagem.</p>
        </div>
        <div className="panel-actions">
          <button className="btn primary" onClick={handleOpenCreate} type="button">Cadastrar camera</button>
        </div>
      </div>

      <div className="card">
        <div className="card-head">Cameras cadastradas</div>
        <div className="card-body table-wrap">
          {loading ? <div className="empty">Carregando...</div> : null}
          {!loading && cameras.length ? (
            <table>
              <thead>
                <tr><th>Nome</th><th>Localizacao</th><th>Tipo</th><th>Portao</th><th>Acoes</th></tr>
              </thead>
              <tbody>
                {cameras.map((camera) => (
                  <tr key={camera.id}>
                    <td>{camera.nome}</td>
                    <td>{camera.localizacao}</td>
                    <td>{camera.tipo}</td>
                    <td className="mono">{camera.porta_usb || "-"}</td>
                    <td>
                      <div className="actions">
                        <button className="btn" onClick={() => handleOpenEdit(camera)} type="button">Editar</button>
                        <button className="btn err" onClick={() => handleDelete(camera.id)} type="button">Remover</button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : null}
          {!loading && !cameras.length ? <div className="empty">Nenhuma camera cadastrada.</div> : null}
        </div>
      </div>

      <Modal open={open} title={editingCamera ? "Editar camera" : "Nova camera"} onClose={handleCloseModal}>
        <CameraForm
          backendUrl={backendUrl}
          initialData={editingCamera}
          loading={saving}
          onSubmit={handleSave}
          onClose={handleCloseModal}
          onToast={onToast}
        />
      </Modal>
    </div>
  );
}
