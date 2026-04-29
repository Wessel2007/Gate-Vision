import { useEffect, useState } from "react";
import { fetchLogs } from "../lib/api";
import { formatDateTime, logStatus } from "../lib/utils";

export default function LogsView({ onToast }) {
  const [logs, setLogs] = useState(null);

  useEffect(() => {
    let alive = true;
    fetchLogs()
      .then((data) => { if (alive) setLogs(data); })
      .catch((error) => {
        onToast(`Erro ao carregar historico: ${error.message}`);
        if (alive) setLogs([]);
      });
    return () => { alive = false; };
  }, []);

  return (
    <div className="page-stack">
      <div className="panel-header">
        <div>
          <div className="eyebrow">Rastreabilidade</div>
          <h2 className="section-title">Historico de acessos</h2>
          <p className="section-sub">Ate 200 registros recentes para auditoria da entrada, identificacao da camera e decisao tomada.</p>
        </div>
      </div>

      <div className="card">
        <div className="card-head">Historico de acessos</div>
        <div className="card-body table-wrap">
          {logs === null ? <div className="empty">Carregando...</div> : null}
          {logs && logs.length ? (
            <table>
              <thead>
                <tr><th>Data/Hora</th><th>Placa</th><th>Morador</th><th>Camera</th><th>Status</th></tr>
              </thead>
              <tbody>
                {logs.map((log, index) => {
                  const { label, ok } = logStatus(log);
                  return (
                    <tr key={`${log.registrado_em}-${index}`}>
                      <td>{formatDateTime(log.registrado_em)}</td>
                      <td className="mono">{log.placa_detectada}</td>
                      <td>{log.proprietario || "-"}</td>
                      <td>{log.camera || "-"}</td>
                      <td className={ok ? "table-status-ok" : "table-status-err"}>{label}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          ) : null}
          {logs && !logs.length ? <div className="empty">Sem registros de acesso no momento.</div> : null}
        </div>
      </div>
    </div>
  );
}
