# Projects Page Component Tree

## Component Hierarchy

```
Projects
├── Loading State (conditional)
│   └── RefreshCw (spinner icon)
│
├── Error State (conditional)
│   └── Card
│       └── AlertCircle + error message
│
└── Success State
    ├── Header
    │   ├── Title + Description
    │   └── Refresh Button
    │       └── RefreshCw (icon)
    │
    ├── Empty State (conditional)
    │   └── Card
    │       ├── FolderOpen (icon)
    │       ├── Heading
    │       └── Description
    │
    ├── Project Grid (conditional)
    │   └── Card[] (for each project)
    │       ├── CardHeader
    │       │   ├── FolderOpen (icon)
    │       │   ├── CardTitle (project name)
    │       │   ├── Badge (local/cloud mode)
    │       │   └── CardDescription (last updated)
    │       │
    │       └── CardContent
    │           ├── Statistics Grid
    │           │   ├── Messages Stat
    │           │   │   ├── MessageSquare (icon)
    │           │   │   └── Count
    │           │   └── Files Stat
    │           │       ├── FileText (icon)
    │           │       └── Count
    │           │
    │           ├── Collections Section (conditional)
    │           │   ├── Database (icon)
    │           │   └── Collection[]
    │           │       ├── Collection name (truncated)
    │           │       └── Badge (points count)
    │           │
    │           └── No Collections Warning (conditional)
    │               ├── AlertCircle (icon)
    │               └── Warning message
    │
    └── Summary Card (conditional)
        ├── CardHeader
        │   ├── CardTitle
        │   └── CardDescription
        │
        └── CardContent
            └── Stats Grid (4 columns)
                ├── Total Projects
                ├── Total Messages
                ├── Total Files
                └── Total Collections
```

## State Flow

```
Component Mount
    ↓
loadProjects() called
    ↓
setLoading(true)
    ↓
API call: api.listProjects()
    ↓
    ├─→ Success
    │   ├─→ setProjects(data)
    │   └─→ setLoading(false)
    │       ↓
    │   Render Success State
    │
    └─→ Error
        ├─→ setError(message)
        └─→ setLoading(false)
            ↓
        Render Error State

Auto-refresh (every 30s)
    ↓
loadProjects(true) called
    ↓
setIsRefreshing(true)
    ↓
API call (background)
    ↓
Update data silently
    ↓
setIsRefreshing(false)

Manual Refresh
    ↓
User clicks Refresh button
    ↓
loadProjects() called
    ↓
Same flow as Component Mount
```

## Data Transformations

```
API Response
    ↓
[{
  name: "project-name",
  message_count: 920,
  file_count: 10,
  last_updated: "2025-01-05T12:34:56Z",
  collections: [
    { name: "conv_abc_voyage", points: 64 }
  ]
}]
    ↓
Helper Functions
    ├─→ extractCollectionMode(collection.name)
    │   └─→ Returns: "local" | "cloud" | "unknown"
    │
    ├─→ getTotalVectors(collections)
    │   └─→ Returns: number (sum of all points)
    │
    └─→ formatRelativeTime(last_updated)
        └─→ Returns: "2h ago" | "just now" | etc.
    ↓
Rendered UI Elements
```

## Responsive Breakpoints

```
Mobile (< 768px)
├── Grid: 1 column
├── Summary: 2 columns
└── Header: Stacked

Tablet (768px - 1024px)
├── Grid: 2 columns
├── Summary: 3 columns
└── Header: Side by side

Desktop (> 1024px)
├── Grid: 3 columns
├── Summary: 4 columns
└── Header: Side by side
```

## Icon Usage

| Icon | Purpose | Color |
|------|---------|-------|
| FolderOpen | Project card header, empty state | Primary |
| MessageSquare | Message count stat | Muted |
| FileText | File count stat | Muted |
| Database | Collection section header | Muted |
| RefreshCw | Loading spinner, refresh button | Muted/Primary |
| AlertCircle | Error state, no collections warning | Destructive/Warning |

## Badge Variants

| Variant | Usage | Example |
|---------|-------|---------|
| secondary | Local embedding mode | Gray background |
| info | Cloud embedding mode | Blue background |
| outline | Vector point counts | Border only |

## Key Props & Handlers

```typescript
// Project Card
<Card
  key={project.name}
  className="hover:shadow-lg transition-shadow"
>

// Refresh Button
<button
  onClick={() => loadProjects()}
  disabled={isRefreshing}
  className="..."
>

// Collection with tooltip
<p
  className="text-xs font-mono truncate"
  title={collection.name}
>

// Conditional sections
{projects.length === 0 && <EmptyState />}
{error && <ErrorState />}
{projects.length > 0 && <ProjectGrid />}
```

## CSS Classes Breakdown

### Layout
- `space-y-6` - Vertical spacing between sections
- `grid gap-4` - Grid gap between cards
- `md:grid-cols-2 lg:grid-cols-3` - Responsive columns
- `flex items-center justify-between` - Header layout

### Typography
- `text-3xl font-bold tracking-tight` - Page title
- `text-lg truncate` - Project name
- `text-xs font-mono` - Collection name
- `text-2xl font-bold` - Statistics numbers

### Colors & States
- `text-muted-foreground` - Secondary text
- `bg-primary text-primary-foreground` - Button
- `hover:shadow-lg transition-shadow` - Card hover
- `disabled:opacity-50` - Disabled button

### Spacing
- `pt-6` - Top padding
- `p-2` - All-around padding
- `gap-2, gap-4, gap-6` - Various gaps
- `mb-1, mb-2, mb-4` - Bottom margins

## Performance Optimizations

1. **Conditional Rendering**: Only renders visible state
2. **Key Props**: Proper keys for list items (project.name)
3. **Separate States**: loading vs isRefreshing for better UX
4. **Interval Cleanup**: useEffect returns cleanup function
5. **Memoized Calculations**: Helper functions called on-demand
6. **Efficient Updates**: Only re-renders changed data

## Accessibility Features

1. **Semantic HTML**: Proper heading hierarchy (h2, h3)
2. **ARIA Labels**: Implicit via semantic structure
3. **Focus Management**: Native button focus states
4. **Screen Readers**: Icon + text combinations
5. **Keyboard Navigation**: All interactive elements focusable
6. **Color Contrast**: Passes WCAG AA standards
7. **Tooltips**: Full collection names on hover
8. **Loading States**: Announced via text, not just icons
