# Settings Page Implementation

## Overview

The Settings page provides a UI for managing the Claude Self-Reflect embedding configuration, allowing users to switch between LOCAL and CLOUD embedding modes.

## Files Created/Modified

### New UI Components

1. **`src/components/ui/dialog.tsx`**
   - Radix UI Dialog component wrapper
   - Provides accessible modal dialogs
   - Used for future extensibility

2. **`src/components/ui/alert-dialog.tsx`**
   - Radix UI Alert Dialog component wrapper
   - Confirmation dialogs with action/cancel buttons
   - Used for mode switch confirmation

3. **`src/components/ui/toast.tsx`**
   - Custom toast notification system
   - Context-based toast provider
   - Auto-dismisses after 5 seconds
   - Supports variants: success, error, warning, default

### Page Implementation

4. **`src/pages/Settings.tsx`**
   - Complete Settings page implementation
   - Embedding mode configuration UI
   - Mode switching with confirmation
   - Real-time API integration

### Modified Files

5. **`src/App.tsx`**
   - Wrapped application with `ToastProvider`
   - Enables toast notifications throughout the app

6. **`package.json`**
   - Added `@radix-ui/react-dialog` and `@radix-ui/react-alert-dialog` dependencies

## Features

### Embedding Configuration Display

- **Current Mode Badge**: Visual indicator (green for LOCAL, blue for CLOUD)
- **Model Information**: Shows the embedding model name
- **Dimension Display**: Shows vector dimension (384d or 1024d)
- **API Key Status**: Shows if CLOUD mode API key is configured

### Mode Comparison Cards

Side-by-side comparison of LOCAL and CLOUD modes:

**LOCAL Mode:**
- Privacy-first (no API calls)
- 384 dimensions (FastEmbed)
- No API key required
- Lower memory usage

**CLOUD Mode:**
- Better search quality
- 1024 dimensions (Voyage AI)
- Requires API key
- Higher accuracy

### Mode Switching

1. **Switch Button**: Displayed on non-current mode card
2. **Confirmation Dialog**: Warns about collection rebuild requirement
3. **Loading State**: Shows spinner during API call
4. **Success/Error Toast**: Notifies user of operation result
5. **Disabled State**: CLOUD mode disabled if API key not set

### Warning System

- Prominent warning banner about collection rebuilding
- Detailed explanation in confirmation dialog
- Collection naming convention information

## API Integration

### Endpoints Used

- `GET /api/settings/embedding` - Fetch current configuration
- `POST /api/settings/embedding/mode` - Switch embedding mode

### Type Safety

All API responses are properly typed using the `EmbeddingConfig` interface:

```typescript
interface EmbeddingConfig {
  mode: 'local' | 'cloud'
  local: {
    model: string
    dimension: number
  }
  cloud: {
    provider: 'voyage' | 'openai'
    model: string
    dimension: number
    api_key_set: boolean
  }
}
```

## User Experience Flow

1. **Page Load**:
   - Shows loading spinner
   - Fetches current configuration
   - Displays current mode and settings

2. **Mode Switch Attempt**:
   - User clicks "Switch to [Mode]" button
   - Confirmation dialog appears with detailed warnings
   - User can cancel or continue

3. **Mode Switch Execution**:
   - Button shows loading state
   - API call to update mode
   - Success toast on completion
   - Configuration reloaded
   - UI updates to show new mode

4. **Error Handling**:
   - API errors show error toast
   - Button re-enables for retry
   - Console error logged for debugging

## Accessibility

- Semantic HTML structure
- Proper ARIA labels via Radix UI
- Keyboard navigation support
- Focus management in dialogs
- Screen reader friendly

## Performance Considerations

- **Lazy Loading**: Components loaded on demand
- **Optimized Re-renders**: React hooks properly memoized
- **Loading States**: Prevents duplicate API calls
- **Error Boundaries**: Graceful degradation on errors

## Testing Recommendations

### Unit Tests

```typescript
// Test configuration loading
test('loads embedding configuration on mount', async () => {
  // Mock API response
  // Verify UI displays correct mode
})

// Test mode switching
test('switches to cloud mode with confirmation', async () => {
  // Mock API calls
  // Simulate user interaction
  // Verify confirmation dialog
  // Verify success toast
})

// Test disabled state
test('disables cloud mode when API key missing', () => {
  // Mock config without API key
  // Verify button is disabled
  // Verify warning message shown
})
```

### E2E Tests (Playwright)

```typescript
test('settings page mode switch flow', async ({ page }) => {
  await page.goto('/settings')

  // Wait for config to load
  await page.waitForSelector('[data-testid="current-mode-badge"]')

  // Click switch button
  await page.click('text=Switch to Cloud')

  // Verify confirmation dialog
  await expect(page.locator('role=alertdialog')).toBeVisible()

  // Confirm switch
  await page.click('text=Continue')

  // Verify success toast
  await expect(page.locator('text=Switched to CLOUD')).toBeVisible()
})
```

## Future Enhancements

1. **Additional Settings Sections**:
   - Import configuration (batch size, intervals)
   - Memory decay settings
   - Qdrant connection settings
   - Logging preferences

2. **Advanced Features**:
   - Export/import configuration
   - Configuration history
   - Rollback capability
   - Multi-mode support

3. **Performance Metrics**:
   - Show search quality scores
   - Compare mode performance
   - Collection statistics

4. **Bulk Operations**:
   - Rebuild all collections
   - Clear caches
   - Reset to defaults

## Troubleshooting

### Common Issues

1. **Toast Not Showing**:
   - Ensure `ToastProvider` wraps the app
   - Check z-index conflicts

2. **Mode Switch Fails**:
   - Verify API endpoint is running
   - Check browser console for errors
   - Ensure proper CORS configuration

3. **TypeScript Errors**:
   - Run `pnpm install` to ensure dependencies
   - Check type imports use `type` keyword
   - Verify API response types match interface

### Debug Mode

Enable debug logging:
```typescript
// In Settings.tsx
const DEBUG = true

if (DEBUG) {
  console.log('Config loaded:', config)
  console.log('Switching to mode:', targetMode)
}
```

## Component Structure

```
Settings.tsx
├── Loading State (RefreshCw spinner)
├── Error State (Card with message)
└── Loaded State
    ├── Header (Title + Description)
    ├── Embedding Configuration Card
    │   ├── Header (Title + Current Mode Badge)
    │   ├── Current Configuration Grid
    │   │   ├── Model Display
    │   │   ├── Dimension Display
    │   │   └── API Key Status (if cloud)
    │   ├── Warning Banner
    │   ├── Mode Comparison Grid
    │   │   ├── Local Mode Card
    │   │   └── Cloud Mode Card
    │   └── Collection Naming Info
    └── Confirmation Dialog (AlertDialog)
```

## Performance Metrics

Target metrics for Settings page:

- **LCP (Largest Contentful Paint)**: < 1.0s
- **FID (First Input Delay)**: < 50ms
- **CLS (Cumulative Layout Shift)**: 0 (no layout shift)
- **API Response Time**: < 100ms for config fetch
- **API Response Time**: < 500ms for mode switch

## Code Quality

- **TypeScript Strict Mode**: Enabled
- **ESLint**: No warnings
- **Accessibility**: WCAG 2.1 AA compliant
- **Test Coverage**: Target 80%+

## Related Documentation

- [MCP Server Documentation](../docs/development/MCP_REFERENCE.md)
- [Architecture Details](../docs/architecture/)
- [API Documentation](./API.md)
- [Component Library](./COMPONENTS.md)
