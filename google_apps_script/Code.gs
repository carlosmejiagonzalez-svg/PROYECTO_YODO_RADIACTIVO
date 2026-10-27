// PROPUESTA PARA REVISIÓN. Hacer copia de seguridad antes de migrar o desplegar.
var SHEET_NAME = 'Pacientes';
var LOG_SHEET = 'Log';
var HEADERS = ['Nombre','ID','Entidad','Fecha_Capsula','mCI','Estado','Fecha_Recepcion','Fecha_Administracion','Notas','Agendado','Reporte_Generado','ID_Tratamiento'];

// Ejecutar manualmente desde el editor una sola vez, después de una copia de seguridad.
// No elimina ni sobrescribe códigos existentes. Rechaza códigos repetidos.
function migrarIdentificadoresTratamiento() {
  var lock = LockService.getScriptLock(); lock.waitLock(30000);
  try {
    var sheet = getSheet();
    var headers = sheet.getRange(1, 1, 1, 11).getValues()[0].map(String);
    for (var j = 0; j < 11; j++) if (headers[j].trim() !== HEADERS[j]) throw new Error('Encabezado inesperado en columna ' + (j+1) + ': ' + headers[j]);
    var header12 = String(sheet.getRange(1, 12).getValue()).trim();
    if (header12 && header12 !== HEADERS[11]) throw new Error('La columna 12 está ocupada; no se efectuó la migración.');
    var n = sheet.getLastRow() - 1, values = n ? sheet.getRange(2, 12, n, 1).getValues() : [];
    var seen = {};
    values.forEach(function(r) { var v=limpiar(r[0]); if (v && seen[v]) throw new Error('Código de tratamiento duplicado; no se efectuó la migración.'); if(v) seen[v]=true; });
    var changed=0;
    values.forEach(function(r) { if (!limpiar(r[0])) { r[0]=Utilities.getUuid(); changed++; } });
    sheet.getRange(1,12).setValue(HEADERS[11]);
    if (n) sheet.getRange(2,12,n,1).setValues(values);
    registrarLog('MIGRACION', changed + ' códigos asignados');
    return changed;
  } finally { lock.releaseLock(); }
}
function doGet(e) {
  var lock=LockService.getScriptLock();
  try {
    lock.waitLock(30000);
    var p=e.parameter || {}, sheet=getSheet(); validarEstructura(sheet);
    var action=p.action || '', result;
    if (action==='register') {
      var mci=Number(p.mci);
      if (!limpiar(p.nombre)||!limpiar(p.id)||!limpiar(p.entidad)||!isFinite(mci)||mci<=0||!limpiar(p.fecha)) throw new Error('Datos incompletos o actividad inválida.');
      var codigo=Utilities.getUuid();
      sheet.appendRow([limpiar(p.nombre),limpiar(p.id),limpiar(p.entidad),limpiar(p.fecha),mci,'PENDIENTE AGENDAR','','','','NO','NO',codigo]);
      registrarLog('REGISTRO','Tratamiento '+codigo);
      result={success:true,message:'Tratamiento registrado.',id_tratamiento:codigo};
    } else if (action==='cerrar_trazabilidad') {
      var ids=limpiar(p.ids).split(',').filter(Boolean); if (!ids.length || new Set(ids).size !== ids.length) throw new Error('Lista de códigos inválida.');
      var filas=ids.map(function(id){return buscarFila(sheet,id);});
      filas.forEach(function(f){sheet.getRange(f,11).setValue('SI');});
      registrarLog('CERRAR_TRAZABILIDAD',ids.length+' tratamientos'); result={success:true,message:ids.length+' tratamientos cerrados.'};
    } else {
      var fila=buscarFila(sheet,limpiar(p.id_tratamiento));
      if(action==='agendar') {
        sheet.getRange(fila,10).setValue('SI'); sheet.getRange(fila,6).setValue('PENDIENTE');
      } else if(action==='update') {
        var estados=['PENDIENTE','RECIBIDO','ADMINISTRADA','CANCELADO','DECAIMIENTO'];
        if(estados.indexOf(limpiar(p.estado))<0) throw new Error('Estado inválido.');
        sheet.getRange(fila,6).setValue(limpiar(p.estado));
        if(limpiar(p.fecha_recepcion)) sheet.getRange(fila,7).setValue(limpiar(p.fecha_recepcion));
        if(limpiar(p.fecha_administracion)) sheet.getRange(fila,8).setValue(limpiar(p.fecha_administracion));
        sheet.getRange(fila,9).setValue(limpiar(p.notas));
      } else if(action==='borrar_paciente') {
        throw new Error('La eliminación está deshabilitada hasta definir la política de conservación de registros.');
      } else if(action==='reasignar') {
        var actividad=Number(p.mci);
        if(sheet.getRange(fila,6).getValue()!=='CANCELADO') throw new Error('Solo se puede reasignar un tratamiento cancelado.');
        if(!limpiar(p.nombre)||!limpiar(p.id)||!limpiar(p.entidad)||!limpiar(p.fecha)||!isFinite(actividad)||actividad<=0) throw new Error('Datos de reasignación inválidos.');
        var nuevo=Utilities.getUuid();
        sheet.appendRow([limpiar(p.nombre),limpiar(p.id),limpiar(p.entidad),limpiar(p.fecha),actividad,'PENDIENTE','','',limpiar(p.notas),'SI','NO',nuevo]);
        sheet.getRange(fila,6).setValue('DECAIMIENTO');
        sheet.getRange(fila,9).setValue('Reasignado al tratamiento '+nuevo);
        registrarLog('REASIGNAR',limpiar(p.id_tratamiento)+' -> '+nuevo);
      } else throw new Error('Acción desconocida.');
      registrarLog(action.toUpperCase(),'Tratamiento '+limpiar(p.id_tratamiento)); result={success:true,message:'Operación completada.'};
    }
    return jsonResponse(result);
  } catch(err) { return jsonResponse({success:false,message:err.message}); }
  finally { if(lock.hasLock()) lock.releaseLock(); }
}
function doPost(e) {
  var lock=LockService.getScriptLock();
  try {
    lock.waitLock(30000);
    var body=JSON.parse(e.postData.contents); if(body.confirmar!=='BORRAR_TODO') throw new Error('Falta confirmación.');
    var sheet=getSheet(); validarEstructura(sheet); var n=sheet.getLastRow()-1, count=0;
    if(n) { var vals=sheet.getRange(2,10,n,1).getValues(); vals.forEach(function(r){if(String(r[0]).trim()==='SI'){r[0]='NO';count++;}}); sheet.getRange(2,10,n,1).setValues(vals); }
    registrarLog('RESET_AGENDADOS',count+' tratamientos desagendados');
    return jsonResponse({success:true,message:count+' tratamientos desagendados.'});
  } catch(err) { return jsonResponse({success:false,message:err.message}); }
  finally { if(lock.hasLock()) lock.releaseLock(); }
}
function getSheet() { var s=SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SHEET_NAME); if(!s) throw new Error('Hoja Pacientes no encontrada.'); return s; }
function validarEstructura(sheet) { var h=sheet.getRange(1,1,1,12).getValues()[0]; for(var i=0;i<12;i++) if(String(h[i]).trim()!==HEADERS[i]) throw new Error('Estructura incompatible. Realice y verifique la migración.'); }
function buscarFila(sheet,codigo) {
  if(!codigo) throw new Error('Código de tratamiento requerido.');
  var n=sheet.getLastRow()-1, matches=[]; if(n) sheet.getRange(2,12,n,1).getValues().forEach(function(r,i){if(limpiar(r[0])===codigo) matches.push(i+2);});
  if(matches.length!==1) throw new Error('Código de tratamiento no encontrado o duplicado.'); return matches[0];
}
function limpiar(v) { return v==null ? '' : String(v).trim(); }
function jsonResponse(o) { return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON); }
function registrarLog(a,d) { try { var s=SpreadsheetApp.getActiveSpreadsheet().getSheetByName(LOG_SHEET); if(s) s.appendRow([new Date(),a,d]); } catch(_) {} }
