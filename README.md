<p align="center"><img src="images/logo.png" alt="Magic Links" width="420"></p>

# Magic Links per Home Assistant

Link **senza autenticazione** per lanciare un'automazione, uno script o una scena, con scadenza configurabile e una plancia per creare, modificare e condividere i link.

## Funzioni
- Link `https://<tuo-ha>/api/magic_link/<token>` con token casuale a 192 bit
- **Scadenza**: 24h, 48h, fino a una data oppure sempre valido; limite di usi facoltativo
- **Persona associata**: ogni link ha un nome e un campo «Assegnato a»; vengono tracciati usi e ultimo utilizzo
- **Modifica** di qualsiasi link già creato (nome, persona, azione, scadenza, limite usi), azzeramento del contatore e rigenerazione del token
- **Azioni preferite**: marca con ★ le azioni che usi di più; compaiono in cima alla lista di scelta e come scorciatoie nella plancia
- **Plancia** nella sidebar (solo admin) con statistiche, ricerca, filtri, copia, condividi, modifica, elimina
- **Configurazione da interfaccia grafica** (URL esterno, scadenza predefinita, pagina di conferma, anti brute-force, voce in sidebar)
- Pagina di conferma prima dell'esecuzione (le anteprime di WhatsApp/Telegram non lanciano l'azione)
- Blocco IP dopo N token errati (configurabile)
- Dati in `.storage/magic_links` (inclusi nei backup)

## Installazione (HACS)
1. HACS → menu ⋮ → **Repository personalizzati**
2. URL: `https://github.com/andreadodo/magic_links` — categoria **Integrazione**
3. Scarica **Magic Links** e riavvia Home Assistant
4. **Impostazioni → Dispositivi e servizi → Aggiungi integrazione → Magic Links**

Per cambiare le opzioni in seguito: la voce dell'integrazione → **Configura**.

> **Aggiornando dalla 1.0**: se hai `magic_links:` in `configuration.yaml`, la configurazione viene importata automaticamente al riavvio e poi puoi rimuoverla. I link già creati restano.

## Evento `magic_link_used`
Ogni uso genera un evento con `link_id`, `label`, `assigned_to`, `target`:

```yaml
trigger:
  - platform: event
    event_type: magic_link_used
action:
  - service: notify.notify
    data:
      message: "{{ trigger.event.data.assigned_to }} ha usato «{{ trigger.event.data.label }}»"
```

## Note di sicurezza
Chiunque abbia il link può eseguire l'azione finché è valido: usa scadenze brevi e limiti di usi per le azioni sensibili e non collegare azioni che aprono accessi critici senza ulteriori controlli. Con la pagina di conferma disattivata, le anteprime dei messaggi possono far partire l'azione da sole.
