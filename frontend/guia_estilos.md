# Sistema de Diseño — Competizione

---

## Identidad visual general

App web oscura de estética **gaming/esports**: densa, técnica y minimalista. Sin gradientes decorativos exuberantes; la profundidad se logra con capas sutiles de grises casi-negros. El único color vivo es el rojo carmesí del acento.

---

## Paleta de colores

```js
// Fondos (de más oscuro a más claro)
bg:  '#0b0b0f'   // fondo raíz — negro azulado
s1:  '#101015'   // capa 1 (sidebar, paneles laterales)
s2:  '#16161d'   // capa 2 (cards, contenedores)
s3:  '#1e1e27'   // capa 3 (inputs, elementos internos)
s4:  '#252530'   // capa 4 (botones secundarios, placeholders)

// Bordes
bd:  'rgba(255,255,255,0.07)'   // borde estándar
bdM: 'rgba(255,255,255,0.13)'   // borde hover/énfasis

// Acento (único color de marca)
ac:  '#d0184f'                   // rojo carmesí principal
acD: 'rgba(208,24,79,0.15)'     // acento translúcido (fondos de tags, highlights)
acL: '#f02060'                   // acento brillante (hover)

// Texto
tx:  '#eaeaf0'                   // texto primario (blanco cálido-frío)
tx2: 'rgba(234,234,240,0.55)'   // texto secundario
tx3: 'rgba(234,234,240,0.28)'   // texto terciario / metadatos

// Colores semánticos adicionales (solo en tags/badges)
// green:  bg rgba(34,197,94,0.13)   → color #4ade80
// orange: bg rgba(251,146,60,0.13)  → color #fb923c
// blue:   bg rgba(99,179,237,0.13)  → color #63b3ed
```

### Variables CSS globales

Declarar en `:root` del documento:

```css
:root {
  --ac:     #d0184f;
  --ac-dim: rgba(208,24,79,0.15);
  --ac-l:   #f02060;
}
```

---

## Tipografía

Tres familias con roles muy definidos. Importar desde Google Fonts:

```html
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500;9..40,600&family=Space+Mono:wght@400;700&display=swap" rel="stylesheet">
```

| Token | Fuente | Uso |
|-------|--------|-----|
| `fH` | **Space Grotesk** 700 | Títulos, logotipo, números grandes, headings de sección |
| `fB` | **DM Sans** 300–600 | Cuerpo de texto, labels, párrafos, botones |
| `fM` | **Space Mono** 400/700 | Metadatos, timestamps, rangos (LP, rank), tags, subtítulos técnicos |

### Escalas tipográficas

```css
/* Logotipo */
font-family: Space Grotesk; font-size: 19–22px; font-weight: 700; letter-spacing: -0.6px;

/* H1 de pantalla */
font-family: Space Grotesk; font-size: 21–36px; font-weight: 700; letter-spacing: -0.5px a -1.2px;

/* H2 de sección */
font-family: Space Grotesk; font-size: 15px; font-weight: 600;

/* Número stat grande */
font-family: Space Grotesk; font-size: 30px; font-weight: 700; letter-spacing: -1px; line-height: 1;

/* Cuerpo */
font-family: DM Sans; font-size: 13px; font-weight: 400;

/* Label de input */
font-family: DM Sans; font-size: 12px; font-weight: 500; color: tx2;

/* Metadato / monospace */
font-family: Space Mono; font-size: 10px; letter-spacing: 1–1.2px; text-transform: uppercase;
```

---

## Espaciado y bordes

```js
r:  '5px'    // border-radius estándar (botones, inputs, cards pequeñas)
r2: '10px'   // border-radius mayor (cards principales, contenedores)

// Padding típico por contexto
// Cards principales:  18px
// TopBar:             22px 28px (solo arriba)
// Contenido de vista: 20px 28px 28px
// Items de sidebar:   10px 22px
// Logo en sidebar:    26px 22px 24px
```

---

## Layout — AppShell

Estructura de **dos columnas fijas** que ocupa el 100% del viewport (`overflow: hidden`):

```
┌─────────────────────────────────────────────────────┐
│  SIDEBAR (220px fijo)    │  MAIN CONTENT (flex: 1)  │
│  background: s1          │  overflow: hidden         │
│  border-right: 1px bd    │                           │
│                          │  ┌── TopBar ───────────┐  │
│  Logo  (26px 22px)       │  │ H1 + subtítulo      │  │
│  ────────────────────    │  └─────────────────────┘  │
│  Nav items               │  ┌── Scroll Area ──────┐  │
│  ────────────────────    │  │ padding 20px 28px   │  │
│  Avatar + user info      │  │ overflowY: auto     │  │
└─────────────────────────────────────────────────────┘
```

### Sidebar

```js
// Contenedor
{ width: 220, background: T.s1, borderRight: `1px solid ${T.bd}`, height: '100%' }

// Ítem de navegación — ACTIVO
{
  borderLeft: `2px solid ${T.ac}`,
  background: T.acD,
  color: T.tx,
  fontWeight: 600,
}

// Ítem de navegación — INACTIVO
{
  borderLeft: '2px solid transparent',
  color: T.tx2,
  fontWeight: 400,
  // hover: background rgba(255,255,255,0.03)
}

// Logo
// "C" → color: ac | resto → color: tx
// Subtítulo debajo: fM, 10px, tx3, letterSpacing 1.2, uppercase

// Footer del sidebar (usuario)
// Avatar 30px + nombre (12px, 600) + rank · LP (fM, 10px, tx3)
```

### TopBar

```js
// Sin fondo propio ni borde inferior
{ padding: '22px 28px 0' }

// Izquierda: botón back (opcional, 32×32, bg s2, border bd) + H1 + subtítulo
// Derecha: slot de acción + icono notificaciones (34×34 circular) + avatar 34px
// El icono de notificaciones tiene un punto rojo (ac) posicionado absolute top-right
```

---

## Componentes primitivos

### `Btn` — Botón

```js
// VARIANTES
// primary:  background ac, color tx, sin borde
// ghost:    background transparent, border 1px bd, color tx
// disabled: background s4, color tx3, cursor not-allowed

// TAMAÑOS
// sm (small): padding 6px 13px, fontSize 12px
// default:    padding 10px 20px, fontSize 13px

// ESTILOS COMUNES
{
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  gap: 6,
  borderRadius: '5px',   // T.r
  fontWeight: 500,
  fontFamily: 'DM Sans',
  letterSpacing: 0.2,
  whiteSpace: 'nowrap',
  transition: 'filter .12s, background .12s',
  // hover (si no disabled): filter brightness(1.1)
}
```

### `Tag` — Badge de estado

```js
{
  display: 'inline-flex',
  alignItems: 'center',
  padding: '3px 8px',
  borderRadius: 4,
  fontSize: 10,
  fontWeight: 700,
  fontFamily: 'Space Mono',
  letterSpacing: 0.8,
  textTransform: 'uppercase',
}

// VARIANTES DE COLOR
// ac     → background acD,                  color ac
// green  → background rgba(34,197,94,0.13), color #4ade80
// orange → background rgba(251,146,60,0.13),color #fb923c
// blue   → background rgba(99,179,237,0.13),color #63b3ed
// default→ background s4,                   color tx2
```

### `Input` — Campo de texto

```js
// Wrapper del campo
{
  background: T.s3,
  border: `1px solid ${T.bd}`,
  borderRadius: '5px',   // T.r
  padding: '10px 13px',
  display: 'flex',
  alignItems: 'center',
  gap: 10,
  transition: 'border .12s',
}

// Label (encima del campo)
{ fontSize: 12, fontWeight: 500, color: T.tx2, letterSpacing: 0.3, marginBottom: 6 }

// <input> interno
{ background: 'transparent', border: 'none', outline: 'none', color: T.tx, fontSize: 13 }

// Soporte para icono SVG a la izquierda (gap 10px entre icono e input)
```

### `Ava` — Avatar generado

```js
// Color generado automáticamente a partir del nombre del usuario:
// hue = suma de charCodes del nombre % 360
// background: oklch(0.32 0.1 {hue})
// color texto: oklch(0.88 0.08 {hue})
// Muestra las 2 primeras letras del nombre en mayúscula

// Borde con ring activo: border 2px solid ac
// Borde inactivo:        border 2px solid rgba(255,255,255,0.08)

// Indicador de estado online (círculo bottom-right, border 2px solid bg):
// gaming → color ac (rojo)
// online → color #4ade80 (verde)
// offline→ color s4 (gris)
```

### `Icon` — Icono SVG

```js
// SVG con viewBox "0 0 24 24"
// stroke: currentColor, strokeWidth: 2
// strokeLinecap: round, strokeLinejoin: round
// Estilo: Feather Icons
// Tamaño por defecto: 15px
```

---

## Patrones de card

### Card estándar

```js
{
  background: T.s2,
  border: `1px solid ${T.bd}`,
  borderRadius: T.r2,    // 10px
  padding: '18px',
  transition: 'border .12s',
  // hover → borderColor: T.bdM
}
```

### Card con acento superior (estado activo)

Añadir un elemento `div` con posición absoluta en el top del card:

```js
{
  position: 'absolute',
  top: 0, left: 0, right: 0,
  height: 2,
  background: T.ac,   // o T.s4 si inactivo
}
// El card padre necesita: position: 'relative', overflow: 'hidden'
```

---

## Grids y listas

```js
// Grid de stats (dashboard)
{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }

// Grid de cards de torneo
{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }

// Stat card — interior
// Label:  10px, tx3, uppercase, letterSpacing 1, marginBottom 10px
// Valor:  30px, Space Grotesk 700, letterSpacing -1
// Sub:    11px, tx3, marginTop 6px

// Lista tipo feed
// Cada ítem: display flex, alignItems center, gap 12px, padding 11px 0
// Separador: borderBottom 1px solid bd (excepto último)
// Timestamp: 10px, tx3, Space Mono, whiteSpace nowrap
```

---

## Microinteracciones y transiciones

| Elemento | Propiedad | Valor |
|----------|-----------|-------|
| Botones | `filter` | `brightness(1.1)` en hover |
| Cards | `borderColor` | `bd` → `bdM` en hover |
| Nav sidebar | `background` | `rgba(255,255,255,0.03)` en hover |
| Todos | Duración | `0.12s` (nunca `all`, siempre propiedades específicas) |
| Cambio de ruta | `opacity` + `translateY` | fadeIn 0.22s, `cubic-bezier(.2,.7,.3,1)`, `8px → 0` |

```css
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}
.route-fade { animation: fadeIn .22s cubic-bezier(.2,.7,.3,1); }
```

---

## Pantalla de Auth — Patrón split

```
┌────────────────────────┬──────────────────────────┐
│  BRANDING PANEL        │  FORM PANEL               │
│  (520px fijo, bg: s1)  │  (flex:1, centrado)       │
│                        │                           │
│  Decoración abs.:      │  maxWidth: 380px          │
│  · 2 círculos con      │  H1: 26px, fH, fw 700     │
│    border bd           │  p:  14px, tx2            │
│  · radial-gradient     │  Inputs con gap: 14px     │
│    ac-dim en bottom    │  Btn primary ancho 100%   │
│                        │                           │
│  Logo 22px fH          │  Link a register/login    │
│  H2 36px fH -1.2       │  (13px, tx2 + ac)         │
│  Lista de features:    │                           │
│  · dot ac (8px)        │                           │
│  · título + descripción│                           │
└────────────────────────┴──────────────────────────┘
```

```js
// Decoración del panel de branding (posición absoluta)
// Círculo 1: top -120px, left -120px, 400×400px, border 1px bd
// Círculo 2: top -60px,  left -60px,  260×260px, border 1px bdM
// Glow:      bottom -100px, right -80px, 320×320px,
//            radial-gradient(circle, ac-dim 0%, transparent 70%)
```

---

## Scrollbar personalizada

```css
::-webkit-scrollbar       { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.12); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.22); }
```

---

## Reset y base global

```css
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html, body { height: 100%; overflow: hidden; background: #0b0b0f; }
body { font-family: 'DM Sans', sans-serif; color: #eaeaf0; }
input, button, select, textarea { font-family: inherit; }
```

---

## Checklist de implementación

- [ ] Importar las tres fuentes de Google Fonts (Space Grotesk, DM Sans, Space Mono)
- [ ] Declarar variables CSS `--ac`, `--ac-dim`, `--ac-l` en `:root`
- [ ] Definir objeto de tokens `T` con toda la paleta y tipografía
- [ ] Aplicar reset global y `overflow: hidden` en `html, body`
- [ ] Implementar AppShell con sidebar de 220px + área de contenido con scroll
- [ ] Crear primitivos `Btn`, `Tag`, `Input`, `Ava`, `Icon` como componentes reutilizables
- [ ] Añadir scrollbar personalizada con CSS webkit
- [ ] Implementar animación `fadeIn` para transiciones de ruta
- [ ] Usar siempre `transition: 0.12s` con propiedades específicas (nunca `all`)