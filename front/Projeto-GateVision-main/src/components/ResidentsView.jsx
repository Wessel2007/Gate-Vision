import { useEffect, useState } from "react";
import Modal from "./Modal";
import { deleteResident, fetchResidents, saveResident } from "../lib/api";
import { formatCPF, onlyPlate } from "../lib/utils";

function ResidentForm({ onSubmit, onClose, loading }) {
  const [form, setForm] = useState({
    nome: "",
    cpf: "",
    apartamento: "",
    torre: "",
    placa: "",
    veiculo: ""
  });

  function updateField(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  return (
    <form className="form-grid" onSubmit={(event) => { event.preventDefault(); onSubmit(form); }}>
      <div><label className="login-sub">Nome completo</label><input required className="input" value={form.nome} onChange={(event) => updateField("nome", event.target.value)} /></div>
      <div><label className="login-sub">CPF</label><input required className="input" maxLength={14} value={form.cpf} onChange={(event) => updateField("cpf", formatCPF(event.target.value))} /></div>
      <div><label className="login-sub">Apartamento</label><input required className="input" value={form.apartamento} onChange={(event) => updateField("apartamento", event.target.value)} /></div>
      <div><label className="login-sub">Torre</label><input required className="input" value={form.torre} onChange={(event) => updateField("torre", event.target.value.toUpperCase())} /></div>
      <div><label className="login-sub">Placa</label><input required className="input mono" maxLength={7} value={form.placa} onChange={(event) => updateField("placa", onlyPlate(event.target.value))} /></div>
      <div><label className="login-sub">Veiculo</label><input className="input" value={form.veiculo} onChange={(event) => updateField("veiculo", event.target.value)} /></div>
      <div className="form-actions modal-actions">
        <button className="btn primary" type="submit" disabled={loading}>{loading ? "Salvando..." : "Salvar Cadastro"}</button>
        <button className="btn" type="button" onClick={onClose}>Cancelar</button>
      </div>
    </form>
  );
}

function ResidentsTable({ residents, readOnly, onDelete }) {
  if (!residents.length) return <div className="empty">Nenhum cliente cadastrado.</div>;

  return (
    <table>
      <thead>
        <tr>
          <th>Nome</th><th>CPF</th><th>Apto</th><th>Torre</th><th>Placa</th><th>Veiculo</th><th>Vaga</th>{!readOnly ? <th>Acoes</th> : null}
        </tr>
      </thead>
      <tbody>
        {residents.map((resident) => (
          <tr key={resident.id}>
            <td>{resident.nome}</td>
            <td className="mono">{formatCPF(resident.cpf)}</td>
            <td>{resident.apartamento}</td>
            <td>{resident.torre}</td>
            <td className="mono">{resident.placa}</td>
            <td>{resident.veiculo || "-"}</td>
            <td>-</td>
            {!readOnly ? <td><button className="btn" onClick={() => onDelete(resident.id)} type="button">Excluir</button></td> : null}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default function ResidentsView({ readOnly = false, onToast }) {
  const [residents, setResidents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);

  async function loadResidents() {
    setLoading(true);
    try {
      setResidents(await fetchResidents());
    } catch (error) {
      onToast(`Erro ao carregar clientes: ${error.message}`);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadResidents();
  }, []);

  async function handleSave(form) {
    if (form.cpf.replace(/\D/g, "").length !== 11) {
      onToast("CPF deve ter 11 digitos.");
      return;
    }
    if (onlyPlate(form.placa).length < 7) {
      onToast("Placa invalida (minimo 7 caracteres).");
      return;
    }

    setSaving(true);
    try {
      await saveResident({
        ...form,
        cpf: form.cpf.replace(/\D/g, ""),
        placa: onlyPlate(form.placa)
      });
      onToast("Cadastro salvo com sucesso!", "ok");
      setOpen(false);
      await loadResidents();
    } catch (error) {
      onToast(`Erro ao salvar cadastro: ${error.message}`);
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(personId) {
    if (!window.confirm("Deseja remover este cadastro?")) return;
    try {
      await deleteResident(personId);
      onToast("Cadastro removido.", "ok");
      await loadResidents();
    } catch (error) {
      onToast(`Erro ao remover cadastro: ${error.message}`);
    }
  }

  return (
    <div className="page-stack">
      <div className="panel-header">
        <div>
          <div className="eyebrow">{readOnly ? "Consulta" : "Cadastro residencial"}</div>
          <h2 className="section-title">{readOnly ? "Base de clientes" : "Gestao de moradores e veiculos"}</h2>
          <p className="section-sub">{readOnly ? "Visualizacao em modo leitura para conferencia rapida dos moradores e placas vinculadas." : "Cadastre moradores, associe placas e mantenha a base de acesso sempre atualizada."}</p>
        </div>
        {!readOnly ? (
          <div className="panel-actions">
            <button className="btn primary" onClick={() => setOpen(true)} type="button">Cadastrar placa e morador</button>
          </div>
        ) : null}
      </div>

      <div className="card">
        <div className="card-head">{readOnly ? "Cadastro de Clientes (Leitura)" : "Clientes Cadastrados"}</div>
        <div className="card-body table-wrap">
          {loading ? <div className="empty">Carregando...</div> : <ResidentsTable residents={residents} readOnly={readOnly} onDelete={handleDelete} />}
        </div>
      </div>

      <Modal open={open} title="Novo Cliente / Veiculo" onClose={() => setOpen(false)}>
        <ResidentForm onSubmit={handleSave} onClose={() => setOpen(false)} loading={saving} />
      </Modal>
    </div>
  );
}
