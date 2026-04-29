import { useEffect, useState } from "react";
import Modal from "./Modal";
import { deleteAuthorization, fetchAuthorizations, saveAuthorization } from "../lib/api";
import { defaultDatetime, formatDateTime, onlyPlate } from "../lib/utils";

function AuthorizationForm({ loading, onSubmit, onClose }) {
  const [form, setForm] = useState({
    placa: "",
    nome_autorizado: "",
    motivo: "",
    data_inicio: defaultDatetime(),
    data_fim: defaultDatetime(24)
  });

  function update(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  return (
    <form className="form-grid" onSubmit={(event) => { event.preventDefault(); onSubmit(form); }}>
      <div><label className="login-sub">Placa</label><input required className="input mono" maxLength={7} placeholder="Ex: TMP1A23" value={form.placa} onChange={(event) => update("placa", onlyPlate(event.target.value))} /></div>
      <div><label className="login-sub">Nome do Visitante</label><input required className="input" placeholder="Ex: Pedro Encanador" value={form.nome_autorizado} onChange={(event) => update("nome_autorizado", event.target.value)} /></div>
      <div><label className="login-sub">Motivo</label><input className="input" placeholder="Ex: manutencao, visita, entrega" value={form.motivo} onChange={(event) => update("motivo", event.target.value)} /></div>
      <div />
      <div><label className="login-sub">Inicio</label><input required type="datetime-local" className="input" value={form.data_inicio} onChange={(event) => update("data_inicio", event.target.value)} /></div>
      <div><label className="login-sub">Fim</label><input required type="datetime-local" className="input" value={form.data_fim} onChange={(event) => update("data_fim", event.target.value)} /></div>
      <div className="form-actions modal-actions">
        <button className="btn primary" type="submit" disabled={loading}>{loading ? "Criando..." : "Criar Autorizacao"}</button>
        <button className="btn" onClick={onClose} type="button">Cancelar</button>
      </div>
    </form>
  );
}

export default function AuthorizationsView({ onToast }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);

  async function loadAuthorizations() {
    setLoading(true);
    try {
      setItems(await fetchAuthorizations());
    } catch (error) {
      onToast(`Erro ao carregar autorizacoes: ${error.message}`);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadAuthorizations();
  }, []);

  async function handleSave(form) {
    if (onlyPlate(form.placa).length < 7) {
      onToast("Placa invalida (minimo 7 caracteres).");
      return;
    }
    if (new Date(form.data_fim) <= new Date(form.data_inicio)) {
      onToast("A data de fim deve ser posterior ao inicio.");
      return;
    }

    setSaving(true);
    try {
      await saveAuthorization({
        ...form,
        placa: onlyPlate(form.placa),
        data_inicio: new Date(form.data_inicio).toISOString(),
        data_fim: new Date(form.data_fim).toISOString()
      });
      onToast("Autorizacao criada com sucesso!", "ok");
      setOpen(false);
      await loadAuthorizations();
    } catch (error) {
      onToast(`Erro ao criar autorizacao: ${error.message}`);
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(id) {
    if (!window.confirm("Deseja cancelar esta autorizacao?")) return;
    try {
      await deleteAuthorization(id);
      onToast("Autorizacao cancelada.", "ok");
      await loadAuthorizations();
    } catch (error) {
      onToast(`Erro ao cancelar autorizacao: ${error.message}`);
    }
  }

  return (
    <div className="page-stack">
      <div className="panel-header">
        <div>
          <div className="eyebrow">Permissoes temporarias</div>
          <h2 className="section-title">Liberacoes para visitantes</h2>
          <p className="section-sub">Cadastre acessos com validade limitada para prestadores, entregas e visitantes fora da base principal.</p>
        </div>
        <div className="panel-actions">
          <button className="btn primary" onClick={() => setOpen(true)} type="button">Criar autorizacao</button>
        </div>
      </div>

      <div className="card">
        <div className="card-head">Autorizacoes Ativas</div>
        <div className="card-body table-wrap">
          {loading ? <div className="empty">Carregando...</div> : null}
          {!loading && items.length ? (
            <table>
              <thead>
                <tr><th>Placa</th><th>Visitante</th><th>Motivo</th><th>Inicio</th><th>Validade</th><th>Acoes</th></tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.id}>
                    <td className="mono">{item.placa}</td>
                    <td>{item.nome_autorizado}</td>
                    <td>{item.motivo || "-"}</td>
                    <td>{formatDateTime(item.data_inicio)}</td>
                    <td>{formatDateTime(item.data_fim)}</td>
                    <td><button className="btn err" onClick={() => handleDelete(item.id)} type="button">Cancelar</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : null}
          {!loading && !items.length ? <div className="empty">Nenhuma autorizacao ativa no momento.</div> : null}
        </div>
      </div>

      <Modal open={open} title="Nova Autorizacao Temporaria" onClose={() => setOpen(false)}>
        <AuthorizationForm loading={saving} onSubmit={handleSave} onClose={() => setOpen(false)} />
      </Modal>
    </div>
  );
}
