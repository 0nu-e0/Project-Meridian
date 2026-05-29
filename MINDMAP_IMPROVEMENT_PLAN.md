# Mindmap Screen Improvement Plan

## Current Issues Identified

1. **Grid Rendering**: Fixed grid size (25px) doesn't scale with zoom, causing visual inconsistencies
2. **Zoom Behavior**: No zoom controls or smooth zoom functionality implemented
3. **Object Tracking**: Node snapping uses hardcoded grid size, doesn't adapt to zoom level
4. **No Spatial Indexing**: No efficient way to track/find objects across large canvas
5. **Performance**: Grid redraws entire viewport on every paint, no optimization for large canvases

---

## Phase 0: Spatial Object Tracking System (NEW - FOUNDATION)

### Goals
- Implement efficient spatial indexing for fast object lookup
- Add automatic bounding box tracking for all content
- Enable instant "zoom to content" calculations
- Prepare foundation for minimap and performance optimizations

### Why This Phase is Critical
Without proper object tracking, "zoom to fit" operations require iterating through ALL scene items, which is O(n) complexity. With spatial indexing, we can:
- Calculate content bounds in O(1) time
- Find objects in a region quickly (for minimap, selection, etc.)
- Enable future features like spatial queries and collision detection

### Implementation Tasks

#### 0.1 Create Spatial Tracking Manager
**File**: `ui/mindmap_screen.py` - New SpatialTracker class
- Track all NodeItems with their bounding rectangles
- Maintain global content bounding box (updated incrementally)
- Provide O(1) access to content bounds for zoom-to-fit
- Auto-update when nodes move/resize/add/delete

**Technical Approach**:
```python
class SpatialTracker:
    """
    Efficiently tracks objects in scene space for fast queries.
    Maintains incrementally-updated bounding box of all content.
    """
    def __init__(self):
        self.objects = {}  # {node_id: QRectF (scene bounds)}
        self._content_bounds = None  # Cached bounding box of all content
        self._dirty = False  # Flag to recalculate bounds

    def add_object(self, node_id, bounds_rect):
        """Add or update object bounds"""
        self.objects[node_id] = bounds_rect
        self._expand_bounds(bounds_rect)

    def remove_object(self, node_id):
        """Remove object and mark bounds for recalculation"""
        if node_id in self.objects:
            del self.objects[node_id]
            self._dirty = True

    def update_object(self, node_id, new_bounds):
        """Update object position/size"""
        self.objects[node_id] = new_bounds
        self._expand_bounds(new_bounds)

    def get_content_bounds(self):
        """Get bounding box of all content - O(1) if not dirty"""
        if self._dirty or self._content_bounds is None:
            self._recalculate_bounds()
        return self._content_bounds

    def _expand_bounds(self, rect):
        """Incrementally expand bounds (faster than full recalc)"""
        if self._content_bounds is None:
            self._content_bounds = QRectF(rect)
        else:
            self._content_bounds = self._content_bounds.united(rect)

    def _recalculate_bounds(self):
        """Full recalculation when object is removed"""
        if not self.objects:
            self._content_bounds = QRectF(0, 0, 0, 0)
        else:
            bounds = None
            for rect in self.objects.values():
                if bounds is None:
                    bounds = QRectF(rect)
                else:
                    bounds = bounds.united(rect)
            self._content_bounds = bounds
        self._dirty = False

    def get_objects_in_rect(self, query_rect):
        """Find all objects intersecting a rectangle (for selection)"""
        return [oid for oid, rect in self.objects.items()
                if rect.intersects(query_rect)]

    def clear(self):
        """Clear all tracked objects"""
        self.objects.clear()
        self._content_bounds = None
        self._dirty = False
```

#### 0.2 Integrate Tracker with GridScene
**File**: `ui/mindmap_screen.py` - GridScene class
- Add `self.spatial_tracker = SpatialTracker()` to __init__
- Hook into scene's itemAdded/itemRemoved signals (if available)
- Provide helper methods for common queries

**Integration Points**:
```python
class GridScene(QGraphicsScene):
    def __init__(self, grid_size=25, parent=None):
        super().__init__(parent)
        self.grid_size = grid_size
        self.spatial_tracker = SpatialTracker()

    def addItem(self, item):
        """Override to track NodeItems"""
        super().addItem(item)
        if isinstance(item, NodeItem):
            bounds = item.sceneBoundingRect()
            self.spatial_tracker.add_object(item.id, bounds)

    def removeItem(self, item):
        """Override to untrack NodeItems"""
        if isinstance(item, NodeItem):
            self.spatial_tracker.remove_object(item.id)
        super().removeItem(item)

    def get_content_bounds(self):
        """Public API for getting all content bounds"""
        return self.spatial_tracker.get_content_bounds()
```

#### 0.3 Update NodeItem to Notify Tracker
**File**: `ui/custom_widgets/mindmap_nodes.py` - NodeItem class
- Notify scene's spatial tracker when position changes
- Notify when size changes (during resize)
- Hook into existing `itemChange()` method

**Technical Approach**:
```python
class NodeItem(QGraphicsEllipseItem):
    def itemChange(self, change, value):
        # ... existing selection handling ...

        if change == QGraphicsItem.ItemPositionHasChanged:
            self.notify_connections()
            # NEW: Update spatial tracker
            if self.scene() and hasattr(self.scene(), 'spatial_tracker'):
                bounds = self.sceneBoundingRect()
                self.scene().spatial_tracker.update_object(self.id, bounds)

        # ... rest of method ...

    def setSizeKeepCenter(self, new_w, new_h):
        # ... existing resize logic ...

        # NEW: Update spatial tracker after resize
        if self.scene() and hasattr(self.scene(), 'spatial_tracker'):
            bounds = self.sceneBoundingRect()
            self.scene().spatial_tracker.update_object(self.id, bounds)
```

#### 0.4 Implement Zoom to Content
**File**: `ui/mindmap_screen.py` - MindMapScreen class
- Add "Zoom to Fit All" button
- Calculate content bounds using spatial tracker
- Fit view to show all content with padding

**Technical Approach**:
```python
def zoom_to_content(self, padding=50):
    """Zoom view to fit all content with padding"""
    content_bounds = self.scene.get_content_bounds()

    if content_bounds.isNull() or content_bounds.isEmpty():
        # No content, reset to center
        self.view.resetTransform()
        return

    # Add padding around content
    padded_bounds = content_bounds.adjusted(-padding, -padding,
                                            padding, padding)

    # Fit the view to show padded bounds
    self.view.fitInView(padded_bounds, Qt.KeepAspectRatio)

    # Optional: Clamp zoom level to reasonable range
    current_scale = self.view.transform().m11()
    if current_scale > 3.0:  # Too zoomed in
        self.view.resetTransform()
        self.view.scale(3.0, 3.0)
        self.view.centerOn(content_bounds.center())
    elif current_scale < 0.1:  # Too zoomed out
        self.view.resetTransform()
        self.view.scale(0.1, 0.1)
        self.view.centerOn(content_bounds.center())
```

#### 0.5 Add Debug Visualization (Optional)
**File**: `ui/mindmap_screen.py` - GridScene class
- Add option to draw content bounding box (for debugging)
- Show tracked object count in UI
- Visualize spatial index structure

**Benefits**:
- Verify tracker is working correctly
- Debug boundary calculation issues
- Performance monitoring

---

## Phase 1: Enhanced Grid System

### Goals
- Implement adaptive grid that scales with zoom level
- Add multiple grid line styles (major/minor lines)
- Optimize grid rendering performance
- Add configurable grid snapping

### Implementation Tasks

#### 1.1 Create Adaptive Grid Rendering
**File**: `ui/mindmap_screen.py` - GridScene class
- Modify `drawBackground()` to calculate grid spacing based on current zoom/scale
- Implement multi-level grid (fine/medium/coarse lines at different zoom levels)
- Add grid density adjustment based on viewport size
- Cache grid calculations to avoid redundant computation

**Technical Approach**:
```python
# Calculate visible zoom level from view transform
scale_factor = painter.transform().m11()  # Get x-axis scale

# Adaptive spacing: smaller grid at high zoom, larger at low zoom
if scale_factor > 2.0:
    fine_grid = self.grid_size / 2
    major_grid = self.grid_size
elif scale_factor < 0.5:
    fine_grid = self.grid_size * 2
    major_grid = self.grid_size * 4
```

#### 1.2 Add Grid Configuration Options
**File**: `ui/mindmap_screen.py` - MindMapScreen class
- Add grid visibility toggle button
- Add grid size selector (10px, 25px, 50px)
- Add snap-to-grid toggle
- Store grid preferences per mindmap

#### 1.3 Optimize Grid Performance
**File**: `ui/mindmap_screen.py` - GridScene class
- Only draw grid lines within visible viewport bounds
- Implement line batching for fewer draw calls
- Add dirty rectangle tracking to minimize redraws

---

## Phase 2: Professional Zoom System

### Goals
- Add smooth zoom controls with keyboard and mouse support
- Implement zoom-to-fit and zoom-to-selection features
- Add zoom level indicator
- Maintain object positions during zoom operations

### Implementation Tasks

#### 2.1 Add QGraphicsView Zoom Controls
**File**: `ui/mindmap_screen.py` - Create custom ZoomableGraphicsView class
- Subclass QGraphicsView to add zoom functionality
- Implement mouse wheel zoom (Ctrl + scroll)
- Add keyboard shortcuts (Ctrl +/-, Ctrl 0 for reset)
- Implement zoom limits (min: 10%, max: 500%)

**Technical Approach**:
```python
class ZoomableGraphicsView(QGraphicsView):
    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            zoom_factor = 1.15
            if event.angleDelta().y() > 0:
                self.scale(zoom_factor, zoom_factor)
            else:
                self.scale(1/zoom_factor, 1/zoom_factor)
            event.accept()
```

#### 2.2 Create Zoom Control UI
**File**: `ui/mindmap_screen.py` - MindMapScreen class
- Add zoom slider widget in left panel
- Add zoom percentage display
- Add "Zoom to Fit" button (fits all nodes in view)
- Add "Zoom to Selection" button
- Add "Reset Zoom (100%)" button

#### 2.3 Implement Smart Zoom Features
**File**: `ui/mindmap_screen.py` - ZoomableGraphicsView class
- Zoom to fit: Calculate bounding box of all nodes, scale view to fit
- Zoom to selection: Focus on selected nodes
- Zoom follows mouse cursor position
- Smooth zoom animations (optional)

---

## Phase 3: Improved Object Tracking

### Goals
- Fix node snapping to work correctly at all zoom levels
- Improve connection line tracking during node movement
- Add visual feedback for snapping behavior
- Optimize position updates for better performance

### Implementation Tasks

#### 3.1 Fix Grid Snapping System
**File**: `ui/custom_widgets/mindmap_nodes.py` - NodeItem class
- Make grid size configurable (remove hardcoded 25)
- Get grid size from parent scene
- Adjust snapping calculations to account for current zoom
- Add optional snap-to-grid disable mode

**Technical Approach**:
```python
def snapPosition(self):
    # Get grid size from scene instead of hardcoding
    grid_size = self.scene().grid_size if self.scene() else 25

    # Get current view scale for snap threshold
    if self.scene() and self.scene().views():
        view = self.scene().views()[0]
        scale = view.transform().m11()
        # Adjust snap threshold based on zoom
        snap_threshold = grid_size * scale
```

#### 3.2 Enhance Connection Tracking
**File**: `ui/custom_widgets/mindmap_nodes.py` - ConnectionItem class
- Optimize `update_position()` to batch updates
- Add connection smoothing/bezier curves option
- Fix connection position updates during zoom
- Add visual indicators for active connections

#### 3.3 Add Visual Snapping Feedback
**File**: `ui/custom_widgets/mindmap_nodes.py` - NodeItem class
- Highlight nearest grid point when dragging
- Show ghost/preview position while dragging
- Add snap guidelines (alignment with other nodes)
- Optional magnetic snapping animation

---

## Phase 4: Performance & Polish

### Goals
- Optimize rendering for large mindmaps (100+ nodes)
- Add view navigation tools (pan, minimap)
- Improve user experience with animations
- Add undo/redo for node operations

### Implementation Tasks

#### 4.1 Performance Optimizations
**File**: Multiple files
- Implement view frustum culling (don't render offscreen items)
- Use QGraphicsItem caching for static elements
- Batch connection updates instead of individual calls
- Add progressive rendering for complex scenes

#### 4.2 Navigation Enhancements
**File**: `ui/mindmap_screen.py`
- Add minimap widget showing entire canvas
- Implement hand tool for panning (Space + drag)
- Add "Center View" button
- Show viewport indicator in minimap

#### 4.3 User Experience Polish
**File**: Multiple files
- Add smooth animations for zoom/pan operations
- Implement undo/redo stack for node operations
- Add keyboard shortcuts cheat sheet
- Improve handle visibility and hover effects
- Add node selection rectangle (multi-select)

#### 4.4 Advanced Features
**File**: `ui/mindmap_screen.py` and related
- Export mindmap as image (PNG/SVG)
- Auto-layout algorithm for organizing nodes
- Node grouping/containers
- Background image support

---

## Implementation Priority

### Critical Priority (Phase 0 - MUST DO FIRST)
1. **Spatial Tracking System** - Foundation for all other features
2. **Zoom to Content** - Core functionality enabled by tracking
3. **Bounding Box Management** - Required for performance

**Why Phase 0 First?**
- Phases 1-4 will benefit from having spatial tracking in place
- Easier to implement zoom features when we can calculate bounds quickly
- Minimap (Phase 4) requires spatial tracking to work
- Prevents technical debt from hardcoded solutions

### High Priority (Phase 1 & 2)
1. Adaptive grid rendering with zoom support
2. Mouse wheel zoom + zoom controls
3. Fix grid snapping at different zoom levels

### Medium Priority (Phase 3)
1. Connection tracking improvements
2. Visual snapping feedback
3. Grid configuration options

### Low Priority (Phase 4)
1. Performance optimizations
2. Navigation tools (minimap, pan)
3. Undo/redo system
4. Advanced features

---

## Technical Considerations

### Spatial Tracking Design Decisions

**Why Dictionary-Based Tracking?**
- O(1) lookup by node ID
- O(1) add/update operations
- O(n) only when recalculating full bounds (rare)
- Simple to implement and maintain

**Alternative Approaches (NOT Recommended for Your Use Case):**

1. **Quadtree/R-Tree** (Overkill for your needs)
   - Pros: O(log n) spatial queries, great for 10,000+ objects
   - Cons: Complex implementation, overhead for small node counts
   - Verdict: Not worth it unless you have 1000+ nodes

2. **Grid-Based Hash** (Redundant with QGraphicsScene)
   - Pros: Fast region queries
   - Cons: QGraphicsScene already does this internally
   - Verdict: Don't duplicate built-in functionality

3. **Iterating scene.items()** (Current approach - SLOW)
   - Pros: No extra code needed
   - Cons: O(n) for every zoom-to-fit operation
   - Verdict: Replace with dictionary tracker

**Recommended: Simple Dictionary Tracker**
- Tracks just what you need: bounding boxes
- Incremental updates (expand bounds on add/move)
- Only full recalculation when removing objects
- Perfect balance of simplicity and performance

### Coordinate Systems
- **Scene coordinates**: Infinite canvas, grid snapping happens here
- **View coordinates**: What user sees, affected by zoom/pan
- **Item coordinates**: Local to each node

### Zoom Implementation
- Use `QGraphicsView.scale()` for zoom operations
- Track current zoom level for grid calculations
- Transform mouse positions correctly between coordinate systems

### Grid Snapping Logic
```
Node Center Position (Scene) → Snap to Grid → Update Node Top-Left
- Must account for node size to keep center aligned
- Grid size must be accessible from NodeItem
- Snapping should be optional (toggle on/off)
```

### Performance Targets
- 60 FPS for panning/zooming with 50 nodes
- < 100ms for grid redraw
- Smooth interaction at 200% and 50% zoom levels
- **O(1) zoom-to-content calculation** (with spatial tracker)
- **O(1) content bounds query** (with incremental updates)

---

## Testing Plan

### Phase 0 Testing
- Verify spatial tracker updates on node add/remove/move/resize
- Test zoom-to-content with 0, 1, 10, 50, 100 nodes
- Check content bounds calculation accuracy
- Test clear_map() clears spatial tracker
- Verify no memory leaks from tracker references

### Phase 1 Testing
- Test grid rendering at zoom levels: 10%, 50%, 100%, 200%, 500%
- Verify grid toggles on/off correctly
- Check grid performance with large viewport

### Phase 2 Testing
- Test zoom with mouse wheel, buttons, and keyboard
- Verify zoom limits work correctly
- Test zoom-to-fit with 0, 1, and 50+ nodes
- Check zoom level indicator accuracy

### Phase 3 Testing
- Test node snapping at all zoom levels
- Verify connections update correctly during drag
- Test snap feedback visibility
- Check snapping can be disabled

### Phase 4 Testing
- Performance test with 100+ nodes
- Test minimap accuracy and interaction
- Verify undo/redo for all operations
- Test export functionality

---

## Estimated Complexity

- **Phase 1**: Medium - Requires understanding QPainter transforms and grid math
- **Phase 2**: Low-Medium - QGraphicsView has built-in zoom support
- **Phase 3**: Medium-High - Coordinate system transforms are tricky
- **Phase 4**: High - Performance optimization requires profiling and iteration

---

## Dependencies

- PyQt5 QGraphicsView/Scene framework
- Current NodeItem and GridScene classes
- Mindmap save/load system (for grid preferences)

---

## Success Criteria

### Phase 0 Success Criteria
1. ✓ Zoom-to-content works instantly (< 10ms calculation)
2. ✓ Content bounds are always accurate after operations
3. ✓ Spatial tracker memory footprint is minimal
4. ✓ All node operations (add/remove/move/resize) update tracker
5. ✓ Clear map properly resets tracker state

### Overall Success Criteria
1. Grid remains visually consistent at all zoom levels
2. Zoom controls are intuitive and responsive
3. Nodes snap correctly to grid regardless of zoom
4. Performance remains smooth (60 FPS) during interactions
5. User can easily navigate large mindmaps
6. Zoom-to-content button provides instant, accurate framing
