# Collections Page

## Overview
The Collections page provides a comprehensive interface for viewing and managing Qdrant vector database collections used by Claude Self-Reflect.

## Features

### 1. Collection Grid Display
- Cards showing all collections with key metrics
- Responsive grid layout (1-3 columns based on screen size)
- Visual status indicators (green badges for active collections)

### 2. Collection Details
Each collection card displays:
- **Name**: Full collection name (e.g., `csr_project_local_384d`)
- **Status**: Active/inactive indicator with color-coded badge
- **Points Count**: Number of vectors in the collection
- **Vectors Count**: Total indexed vectors
- **Vector Dimension**: Embedding dimension (384d or 1024d)
- **Distance Metric**: Similarity metric (Cosine, Euclidean)
- **Segments Count**: Number of Qdrant segments

### 3. Expandable Details
Click on any collection card to view additional information:
- **Indexed Vectors**: Count of fully indexed vectors
- **Optimizer Status**: Qdrant optimizer state
- **Payload Schema**: JSON schema of stored metadata
- Click again to collapse

### 4. Search and Filter
- Real-time search by collection name
- Case-insensitive filtering
- Shows match count and total collections

### 5. Sorting
- Sort by points count (ascending/descending)
- Toggle sort direction with visual indicator
- Default: Descending (most vectors first)

### 6. Auto-Refresh
- Automatically refreshes every 30 seconds
- Manual refresh button in header
- Maintains selected collection state during refresh

### 7. Summary Statistics
- Total collections count
- Total vectors across all collections
- Filtered results count

## Usage

### Viewing Collections
1. Navigate to the Collections page
2. View all collections in grid format
3. Scroll to see all available collections

### Searching
1. Use the search box to filter collections
2. Type any part of the collection name
3. Results update in real-time

### Viewing Details
1. Click on any collection card
2. Wait for details to load
3. Review additional metadata and schema
4. Click again to collapse

### Sorting
1. Click "Points Count" button to toggle sort
2. ChevronDown icon = descending (high to low)
3. ChevronUp icon = ascending (low to high)

### Refreshing
1. Click "Refresh" button in top-right
2. Or wait 30 seconds for auto-refresh
3. Selected collection remains expanded

## API Integration

### Endpoints Used
- `GET /api/collections/` - List all collections
- `GET /api/collections/{name}` - Get collection details

### Data Flow
1. Component mounts → Load collections
2. User clicks collection → Load collection details
3. Auto-refresh timer → Reload collections every 30s
4. User searches → Filter in-memory
5. User sorts → Sort in-memory

## Performance Considerations

### Optimization Techniques
1. **useMemo**: Memoized filtering and sorting
2. **Auto-refresh**: Only network calls, no re-render unless data changes
3. **Lazy loading**: Details loaded only when collection is expanded
4. **Search**: Client-side filtering (no API calls)

### Bundle Size
- Minimal dependencies (uses existing UI components)
- No heavy libraries for tables or modals
- Optimized with React best practices

## Accessibility

### Keyboard Navigation
- All interactive elements are keyboard accessible
- Tab through search, sort, and collection cards
- Enter/Space to expand/collapse collections

### Screen Readers
- Semantic HTML structure
- ARIA labels on interactive elements
- Status indicators announced properly
- Loading states communicated

### Visual Accessibility
- Color-blind friendly status badges
- High contrast text and backgrounds
- Clear visual focus indicators
- Responsive font sizes

## Error Handling

### Network Errors
- Graceful fallback if collections fail to load
- Error logged to console
- User sees empty state message

### Missing Data
- Safe handling of undefined/null values
- Default values for missing fields
- Type guards for vector configs

## Testing

### Unit Tests
Run tests with: `npm test Collections.test.tsx`

Test coverage includes:
- Loading state rendering
- Collections display
- Search functionality
- Sort toggle
- Collection expansion
- Auto-refresh behavior
- Empty state handling

### Manual Testing Checklist
- [ ] Collections load on page mount
- [ ] Search filters correctly
- [ ] Sort toggles ascending/descending
- [ ] Collection details load when clicked
- [ ] Details collapse when clicked again
- [ ] Auto-refresh works (wait 30s)
- [ ] Manual refresh works
- [ ] Empty state shows when no collections
- [ ] No collections found shows when search has no results
- [ ] Total vectors calculated correctly

## Future Enhancements

### Potential Features
1. Delete collection action
2. Export collection metadata
3. Collection health metrics
4. Vector quality scores
5. Search by dimension or distance metric
6. Batch operations on multiple collections
7. Collection creation wizard
8. Vector count trends over time
9. Storage size per collection
10. Index optimization suggestions

## Related Documentation
- API Documentation: `/api/docs`
- Qdrant Documentation: https://qdrant.tech/documentation/
- MCP Reference: `docs/development/MCP_REFERENCE.md`
