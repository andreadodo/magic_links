# Magic Links per Home Assistant

Link **senza autenticazione** per lanciare un'automazione, uno script o una scena, con scadenza configurabile e una plancia per gestirli e condividerli.

## Funzioni
- Link `https://<tuo-ha>/api/magic_link/<token>` con token casuale a 192 bit
- Scadenza: 24h, 48h, fino a una data oppure sempre valido; limite di usi facoltativo
- Ogni link ha un nome e un campo "Assegnato a"; vengono tracciati usi e ultimo utilizzo
- Plancia nella sidebar (**Link rapidi**, solo admin): copia, condividi, elimina
- Pagina di conferma prima dell'esecuzione (le anteprime di WhatsApp/Telegram non lanciano l'azione)
- Blocco IP dopo 10 token errati in 10 minuti
- Dati salvati in `.storage/magic_links` (inclusi nei backup)

## Installazione (HACS)
1. HACS → menu ⋮ → **Repository personalizzati**
2. URL: `https://github.com/andreadodo/magic_links` — categoria **Integrazione**
3. Scarica **Magic Links** e riavvia Home Assistant
4. Aggiungi a `configuration.yaml` e riavvia:

```yaml
magic_links:
  external_url: https://tuo-dominio.example   # facoltativo
```

Se `external_url` manca, viene usato l'URL esterno configurato in HA. Dietro reverse proxy imposta `use_x_forwarded_for` in `http:`.

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
