import { useEffect, useState } from "react";
import Modal from "./Modal";
import { deleteCamera, fetchCameras, saveCamera } from "../lib/api";

function CameraForm({ loading, onSubmit, onClose }) {
  const [form, setForm] = useState({ nome: "", localizacao: "", tipo_camera_id: "1" });

  function update(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  return (
    <form className="form-grid" onSubmit={(event) => { event.preventDefault(); onSubmit(form); }}>
      <div><label className="login-sub">Nome da Camera</label><input required className="input" placeholder="Ex: CAM-PORT-01" value={form.nome} onChange={(event) => update("nome", event.target.value)} /></div>
      <div><label className="login-sub">Localizacao</label><input required className="input" placeholder="Ex: Portaria Principal" value={form.localizacao} onChange={(event) => update("localizacao", event.target.value)} /></div>
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
        <button className="btn primary" type="submit" disabled={loading}>{loading ? "Salvando..." : "Salvar Camera"}</button>
        <button className="btn" onClick={onClose} type="button">Cancelar</button>
      </div>
    </form>
  );
}

export default function CamerasView({ onToast }) {
  const [cameras, setCameras] = useState([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);

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
      await saveCamera(form);
      onToast("Camera salva com sucesso!", "ok");
      setOpen(false);
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

  return (
    <div className="page-stack">
      <div className="panel-header">
        <div>
          <div className="eyebrow">Infraestrutura</div>
          <h2 className="section-title">Cameras do sistema</h2>
          <p className="section-sub">Cadastre os pontos de captura e organize os equipamentos de entrada, saida e garagem.</p>
        </div>
        <div className="panel-actions">
          <button className="btn primary" onClick={() => setOpen(true)} type="button">Cadastrar camera</button>
        </div>
      </div>

      <div className="card">
        <div className="card-head">Cameras Cadastradas</div>
        <div className="card-body table-wrap">
          {loading ? <div className="empty">Carregando...</div> : null}
          {!loading && cameras.length ? (
            <table>
              <thead>
                <tr><th>Nome</th><th>Localizacao</th><th>Tipo</th><th>Acoes</th></tr>
              </thead>
              <tbody>
                {cameras.map((camera) => (
                  <tr key={camera.id}>
                    <td>{camera.nome}</td>
                    <td>{camera.localizacao}</td>
                    <td>{camera.tipo}</td>
                    <td><button className="btn" onClick={() => handleDelete(camera.id)} type="button">Remover</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : null}
          {!loading && !cameras.length ? <div className="empty">Nenhuma camera cadastrada.</div> : null}
        </div>
      </div>

      <Modal open={open} title="Nova Camera" onClose={() => setOpen(false)}>
        <CameraForm loading={saving} onSubmit={handleSave} onClose={() => setOpen(false)} />
      </Modal>
    </div>
  );
}
