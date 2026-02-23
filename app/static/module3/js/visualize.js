// Babylon.js setup
const canvas = document.getElementById('renderCanvas');
const engine = new BABYLON.Engine(canvas, true);
const scene = new BABYLON.Scene(engine);
scene.clearColor = new BABYLON.Color4(0.04, 0.06, 0.10, 1);

// Enable anti-aliasing for smoother rendering
scene.getEngine().setHardwareScalingLevel(1 / window.devicePixelRatio);

// ==================== PBR ENVIRONMENT SETUP ====================
// Create default PBR environment with Image-Based Lighting (IBL)
const hdrTexture = BABYLON.CubeTexture.CreateFromPrefilteredData(
    "https://playground.babylonjs.com/textures/environment.env",
    scene
);
scene.environmentTexture = hdrTexture;
scene.environmentIntensity = 1.0;

// Create skybox for reflections (optional)
const skybox = scene.createDefaultSkybox(hdrTexture, true, 1000, 0.3);

// ==================== PBR MATERIAL RECIPES ====================
const PBR_RECIPES = {
    // Walls - Plaster/Drywall (matte finish)
    'wall': {
        baseColor: new BABYLON.Color3(0.92, 0.92, 0.88),
        metallic: 0.0,
        roughness: 0.95,
        textureNames: {
            albedo: 'plaster_albedo.jpg',
            normal: 'plaster_normal.jpg',
            roughness: 'plaster_roughness.jpg'
        }
    },

    // Floors - Dark Wood
    'floor': {
        baseColor: new BABYLON.Color3(0.25, 0.18, 0.12),
        metallic: 0.0,
        roughness: 0.7,
        textureNames: {
            albedo: 'wood_dark_albedo.jpg',
            normal: 'wood_dark_normal.jpg',
            roughness: 'wood_dark_roughness.jpg'
        }
    },

    // Ceilings - White painted surface
    'ceiling': {
        baseColor: new BABYLON.Color3(0.96, 0.96, 0.96),
        metallic: 0.0,
        roughness: 0.9,
        textureNames: {
            albedo: 'paint_white_albedo.jpg',
            normal: 'paint_white_normal.jpg'
        }
    },

    // Doors - Painted wood (satin finish)
    'door': {
        baseColor: new BABYLON.Color3(0.85, 0.82, 0.75),
        metallic: 0.0,
        roughness: 0.4,
        textureNames: {
            albedo: 'door_painted_albedo.jpg',
            normal: 'door_painted_normal.jpg',
            roughness: 'door_painted_roughness.jpg'
        }
    },

    // Windows - Glass with slight tint
    'window': {
        baseColor: new BABYLON.Color3(0.7, 0.85, 0.9),
        metallic: 0.9,
        roughness: 0.05,
        alpha: 0.4,
        textureNames: {
            albedo: 'glass_albedo.jpg'
        }
    },

    // Sink - Polished Steel
    'sink': {
        baseColor: new BABYLON.Color3(0.75, 0.75, 0.75),
        metallic: 1.0,
        roughness: 0.2,
        textureNames: {
            albedo: 'metal_steel_albedo.jpg',
            normal: 'metal_steel_normal.jpg',
            metallic: 'metal_steel_metallic.jpg',
            roughness: 'metal_steel_roughness.jpg'
        }
    },

    // Table - Matte Wood Finish
    'table': {
        baseColor: new BABYLON.Color3(0.55, 0.4, 0.28),
        metallic: 0.0,
        roughness: 0.65,
        textureNames: {
            albedo: 'wood_table_albedo.jpg',
            normal: 'wood_table_normal.jpg',
            roughness: 'wood_table_roughness.jpg'
        }
    },

    // Furniture - Generic wood
    'furniture': {
        baseColor: new BABYLON.Color3(0.5, 0.35, 0.25),
        metallic: 0.0,
        roughness: 0.6,
        textureNames: {
            albedo: 'wood_furniture_albedo.jpg',
            normal: 'wood_furniture_normal.jpg'
        }
    },

    // Roof - Dark tiles
    'roof': {
        baseColor: new BABYLON.Color3(0.2, 0.2, 0.22),
        metallic: 0.0,
        roughness: 0.8,
        textureNames: {
            albedo: 'roof_tile_albedo.jpg',
            normal: 'roof_tile_normal.jpg',
            roughness: 'roof_tile_roughness.jpg'
        }
    },

    // Default - Generic surface
    'default': {
        baseColor: new BABYLON.Color3(0.7, 0.7, 0.7),
        metallic: 0.0,
        roughness: 0.75,
        textureNames: {}
    }
};

// ==================== PBR MATERIAL APPLICATION ====================
function applyPBRMaterials(scene) {
    console.log('Applying PBR materials to scene...');
    let materialsApplied = 0;

    scene.meshes.forEach(mesh => {
        if (!mesh || mesh.name === '__root__' || mesh.name.toLowerCase().includes('snapshot')) {
            return;
        }

        // Determine material type based on mesh name
        const meshName = mesh.name.toLowerCase();
        let recipeKey = 'default';

        // Match mesh name to PBR recipe
        if (meshName.includes('wall') || meshName.includes('vegg') || meshName.includes('ifcwall')) {
            recipeKey = 'wall';
        } else if (meshName.includes('floor') || meshName.includes('gulv') || meshName.includes('slab')) {
            recipeKey = 'floor';
        } else if (meshName.includes('ceiling') || meshName.includes('tak')) {
            recipeKey = 'ceiling';
        } else if (meshName.includes('door') || meshName.includes('dør')) {
            recipeKey = 'door';
        } else if (meshName.includes('window') || meshName.includes('vindu')) {
            recipeKey = 'window';
        } else if (meshName.includes('sink') || meshName.includes('vask')) {
            recipeKey = 'sink';
        } else if (meshName.includes('table') || meshName.includes('bord')) {
            recipeKey = 'table';
        } else if (meshName.includes('furniture') || meshName.includes('møbel') || meshName.includes('furnishing')) {
            recipeKey = 'furniture';
        } else if (meshName.includes('roof') || meshName.includes('tak')) {
            recipeKey = 'roof';
        }

        const recipe = PBR_RECIPES[recipeKey];

        // Create PBR material
        const pbrMaterial = new BABYLON.PBRMetallicRoughnessMaterial(
            `pbr_${mesh.name}`,
            scene
        );

        // Apply base properties
        pbrMaterial.baseColor = recipe.baseColor;
        pbrMaterial.metallic = recipe.metallic;
        pbrMaterial.roughness = recipe.roughness;

        // Handle transparency for glass
        if (recipe.alpha !== undefined) {
            pbrMaterial.alpha = recipe.alpha;
            pbrMaterial.transparencyMode = BABYLON.PBRMaterial.PBRMATERIAL_ALPHABLEND;
        }

        // Enable environment reflections
        pbrMaterial.useRadianceOverAlpha = true;
        pbrMaterial.useSpecularOverAlpha = true;

        // Backface culling for proper 3D rendering
        pbrMaterial.backFaceCulling = true;
        pbrMaterial.twoSidedLighting = false;

        // Store original alpha for X-ray mode
        pbrMaterial.originalAlpha = pbrMaterial.alpha || 1.0;

        // TODO: Load textures if available
        // Example for future texture loading:
        // if (recipe.textureNames.albedo) {
        //     pbrMaterial.baseTexture = new BABYLON.Texture(
        //         `/static/textures/${recipe.textureNames.albedo}`, 
        //         scene
        //     );
        // }

        // Apply material to mesh
        mesh.material = pbrMaterial;
        materialsApplied++;

        console.log(`Applied ${recipeKey} PBR material to: ${mesh.name}`);
    });

    console.log(`✓ Applied ${materialsApplied} PBR materials`);
    return materialsApplied;
}

// Camera
const camera = new BABYLON.ArcRotateCamera('camera', -Math.PI / 2, Math.PI / 2.5, 20, BABYLON.Vector3.Zero(), scene);
camera.attachControl(canvas, true);
camera.wheelPrecision = 50;
camera.minZ = 0.1;
camera.maxZ = 1000;
camera.panningSensibility = 100;
camera.lowerRadiusLimit = 0.5;
camera.upperRadiusLimit = 500;

// Lighting for PBR - softer with environment contribution
// Main ambient light (reduced since IBL provides base lighting)
const light1 = new BABYLON.HemisphericLight('light1', new BABYLON.Vector3(0, 1, 0), scene);
light1.intensity = 0.3; // Reduced from 0.6 for PBR
light1.groundColor = new BABYLON.Color3(0.1, 0.1, 0.15);

// Key directional light (sun simulation)
const light2 = new BABYLON.DirectionalLight('light2', new BABYLON.Vector3(-1, -2, -1), scene);
light2.intensity = 0.5; // Reduced from 0.8 for PBR

// Fill light from opposite side
const light3 = new BABYLON.DirectionalLight('light3', new BABYLON.Vector3(1, 0.5, 1), scene);
light3.intensity = 0.2; // Reduced from 0.4 for PBR

// State
let defectsData = [];
let filteredDefects = [];
let markers = [];
let currentDefectId = null;
let defectsVisible = true;
let isAddMode = false;
let ghostMarker = null;
let xrayMode = false;
let wireframeMode = false;
let loadedMeshes = [];
let modelCenter = BABYLON.Vector3.Zero();
let modelLoaded = false;
let modelBounds = { min: null, max: null, size: null };

// Load 3D model
let rootMesh = null;
let snapshotMeshes = [];
if (window.APP_CONFIG.modelUrl) {
    console.log('Loading model from: ' + window.APP_CONFIG.modelUrl);
    BABYLON.SceneLoader.ImportMeshAsync('', window.APP_CONFIG.modelUrl, '', scene, null, '.glb')
        .then(function (result) {
            console.log('Model loaded successfully, meshes:', result.meshes.length);
            loadedMeshes = result.meshes;
            modelLoaded = true;

            // Update mesh count
            document.getElementById('meshCount').textContent = result.meshes.length;

            // Find Snapshot meshes
            result.meshes.forEach(mesh => {
                if (mesh.name === '__root__') {
                    rootMesh = mesh;
                }

                if (mesh.name && mesh.name.toLowerCase().includes('snapshot')) {
                    mesh.computeWorldMatrix(true);
                    snapshotMeshes.push({
                        mesh: mesh,
                        name: mesh.name,
                        position: mesh.absolutePosition.clone()
                    });
                    mesh.isVisible = false;
                    console.log('Found Snapshot mesh:', mesh.name, 'at', mesh.absolutePosition.x.toFixed(2), mesh.absolutePosition.y.toFixed(2), mesh.absolutePosition.z.toFixed(2));
                }
            });

            // Apply PBR materials to all meshes
            applyPBRMaterials(scene);

            console.log('Total Snapshot meshes found:', snapshotMeshes.length);

            // Center camera on model
            if (result.meshes.length > 0) {
                let min = new BABYLON.Vector3(Number.MAX_VALUE, Number.MAX_VALUE, Number.MAX_VALUE);
                let max = new BABYLON.Vector3(-Number.MAX_VALUE, -Number.MAX_VALUE, -Number.MAX_VALUE);
                result.meshes.forEach(mesh => {
                    if (mesh.getBoundingInfo && mesh.name !== '__root__' && !mesh.name.toLowerCase().includes('snapshot')) {
                        mesh.computeWorldMatrix(true);
                        const boundingInfo = mesh.getBoundingInfo();
                        min = BABYLON.Vector3.Minimize(min, boundingInfo.boundingBox.minimumWorld);
                        max = BABYLON.Vector3.Maximize(max, boundingInfo.boundingBox.maximumWorld);
                    }
                });
                modelCenter = min.add(max).scale(0.5);
                const size = max.subtract(min);
                modelBounds = { min, max, size };

                // Update model size display
                document.getElementById('modelSize').textContent =
                    `${size.x.toFixed(1)} x ${size.y.toFixed(1)} x ${size.z.toFixed(1)}`;

                camera.target = modelCenter;
                camera.radius = size.length() * 1.5;
                console.log('Camera centered at:', modelCenter, 'radius:', camera.radius);

                createMarkersFromSnapshots();
                loadDefects();
            }
        })
        .catch(function (error) {
            console.error('Error loading model:', error);
            loadDefects();
        });
} else {
    console.log('No model URL provided');
    loadDefects();
}

// Fetch and render defects
function loadDefects() {
    fetch('/module3/api/scans/' + window.APP_CONFIG.scanId + '/defects')
        .then(response => response.json())
        .then(defects => {
            defectsData = defects;
            filteredDefects = [...defects];
            renderDefectList(filteredDefects);
            renderDefectMarkers(defects);
            document.getElementById('defectCount').textContent = defects.length;
            document.getElementById('defectStat').textContent = defects.length;
        });
}

function renderDefectList(defects) {
    const listEl = document.getElementById('defectList');

    if (defects.length === 0) {
        listEl.innerHTML = `
                    <div class="empty-state">
                        <i class="fas fa-check-circle"></i>
                        <h3>No Defects Found</h3>
                        <p>No defects match your current filters</p>
                    </div>
                `;
        return;
    }

    listEl.innerHTML = defects.map((d, index) => `
                <div class="defect-card" data-id="${d.defectId}" id="card-${d.defectId}" onclick="toggleDefectCard(${d.defectId})">
                    <div class="defect-header">
                        <span class="defect-title">
                            <i class="fas fa-exclamation-circle" style="color: ${getSeverityColorHex(d.severity)};"></i>
                            Defect <span class="defect-index">#${d.defectId}</span>
                        </span>
                        <span class="status-badge ${getStatusClass(d.status)}">${d.status}</span>
                    </div>
                    <div class="defect-description"><strong>${d.location ? '📍 ' + d.location : 'No location'}</strong> - ${d.element || 'Unknown Element'}</div>
                    <div class="defect-description">${d.defect_type || 'Unknown'}</div>
                    <div class="defect-coords">
                        <span class="coord-item"><span class="coord-label">X:</span> ${d.x.toFixed(2)}</span>
                        <span class="coord-item"><span class="coord-label">Y:</span> ${d.y.toFixed(2)}</span>
                        <span class="coord-item"><span class="coord-label">Z:</span> ${d.z.toFixed(2)}</span>
                    </div>
                    
                    <!-- Expanded content -->
                    <div class="defect-expanded" id="expanded-${d.defectId}">
                        <div class="defect-meta-label">Location</div>
                        <div class="defect-meta-value">${d.location || 'Not specified'}</div>
                        
                        <div class="defect-meta-label">Element</div>
                        <div class="defect-meta-value">${d.element || 'Unknown'}</div>
                        
                        <div class="defect-meta-label">Type</div>
                        <div class="defect-meta-value">${d.defect_type || 'Unknown'}</div>
                        
                        <div class="defect-meta-label">Severity</div>
                        <div class="defect-meta-value" style="color: ${getSeverityColorHex(d.severity)};">${d.severity || 'Medium'}</div>
                        
                        <div class="defect-meta-label">Image</div>
                        <div id="defect-img-${d.defectId}" class="defect-meta-value">
                            <span class="no-image">Loading...</span>
                        </div>
                        
                        <div class="defect-meta-label">Description</div>
                        <div class="defect-meta-value">${d.description || 'No description'}</div>
                        
                        <div class="defect-meta-label">Notes</div>
                        <div id="defect-notes-${d.defectId}" class="defect-notes">Loading...</div>
                        
                        <div class="defect-meta-label">Created</div>
                        <div class="defect-meta-value">${d.created_at || 'Unknown'}</div>
                        
                        <div class="defect-actions">
                            <button class="btn btn-small btn-outline" onclick="event.stopPropagation(); focusDefect(${d.defectId})">
                                <i class="fas fa-crosshairs"></i> Focus
                            </button>
                            <button class="btn btn-small btn-primary" onclick="event.stopPropagation(); openDefectModal(${d.defectId})">
                                <i class="fas fa-edit"></i> Edit
                            </button>
                            <button class="btn btn-small btn-danger" onclick="event.stopPropagation(); deleteDefect(${d.defectId})">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </div>
                </div>
            `).join('');
}

function getStatusClass(status) {
    switch (status) {
        case 'Reported': return 'status-reported';
        case 'Under Review': return 'status-review';
        case 'Fixed': return 'status-fixed';
        default: return 'status-reported';
    }
}

function getStatusColorHex(status) {
    switch (status) {
        case 'Reported': return '#ef4444';
        case 'Under Review': return '#f59e0b';
        case 'Fixed': return '#22c55e';
        default: return '#6b7280';
    }
}

function getSeverityColorHex(severity) {
    switch (severity) {
        case 'Low': return '#22c55e';  // Green
        case 'Medium': return '#f59e0b';  // Yellow/Orange
        case 'High': return '#f97316';  // Orange
        case 'Critical': return '#ef4444';  // Red
        default: return '#f59e0b';  // Default to yellow
    }
}

function truncateText(text, maxLen) {
    if (!text) return '';
    return text.length > maxLen ? text.substring(0, maxLen) + '...' : text;
}

// Search functionality
function searchDefects() {
    applyFilters();
}

// Filter functionality
function filterDefects() {
    applyFilters();
}

// Sort functionality
function sortDefects() {
    applyFilters();
}

function applyFilters() {
    const searchQuery = document.getElementById('defectSearch').value.toLowerCase();
    const statusFilter = document.getElementById('statusFilter').value;
    const sortBy = document.getElementById('sortFilter').value;

    filteredDefects = defectsData.filter(d => {
        const matchesSearch = !searchQuery ||
            (d.description && d.description.toLowerCase().includes(searchQuery)) ||
            d.defectId.toString().includes(searchQuery);
        const matchesStatus = !statusFilter || d.status === statusFilter;
        return matchesSearch && matchesStatus;
    });

    // Sort
    switch (sortBy) {
        case 'newest':
            filteredDefects.sort((a, b) => b.defectId - a.defectId);
            break;
        case 'oldest':
            filteredDefects.sort((a, b) => a.defectId - b.defectId);
            break;
        case 'status':
            const statusOrder = { 'Reported': 0, 'Under Review': 1, 'Fixed': 2 };
            filteredDefects.sort((a, b) => statusOrder[a.status] - statusOrder[b.status]);
            break;
    }

    renderDefectList(filteredDefects);
}

function toggleDefectCard(defectId) {
    const card = document.getElementById('card-' + defectId);
    if (!card) return;

    const wasExpanded = card.classList.contains('expanded');

    // Collapse all cards first
    document.querySelectorAll('.defect-card').forEach(c => {
        c.classList.remove('expanded');
    });

    // Reset all markers to normal size
    markers.forEach(m => {
        m.scaling = new BABYLON.Vector3(1, 1, 1);
    });

    if (!wasExpanded) {
        card.classList.add('expanded');
        loadDefectDetails(defectId);

        // Highlight the marker
        const defectIndex = defectsData.findIndex(d => d.defectId === defectId);
        if (defectIndex >= 0 && defectIndex < markers.length) {
            markers[defectIndex].scaling = new BABYLON.Vector3(1.5, 1.5, 1.5);
        }
    }
}

function loadDefectDetails(defectId) {
    fetch('/module3/api/defects/' + defectId)
        .then(response => response.json())
        .then(data => {
            // Update image
            const imgContainer = document.getElementById('defect-img-' + defectId);
            if (imgContainer) {
                if (data.imageUrls && data.imageUrls.length > 0) {
                    let html = '';
                    data.imageUrls.forEach(url => {
                        html += '<img src="' + url + '" class="defect-thumbnail" onclick="event.stopPropagation(); window.open(\'' + url + '\', \'_blank\')" alt="Defect Image" style="margin-bottom: 5px;">';
                    });
                    imgContainer.innerHTML = html;
                } else {
                    imgContainer.innerHTML = '<span class="no-image">No image attached</span>';
                }
            }

            // Update notes
            const notesEl = document.getElementById('defect-notes-' + defectId);
            if (notesEl) {
                notesEl.textContent = data.notes || 'No notes added';
            }
        })
        .catch(err => console.error('Error loading defect details:', err));
}

// Create markers from GLB Snapshot meshes
function createMarkersFromSnapshots() {
    markers.forEach(m => m.dispose());
    markers = [];

    snapshotMeshes.forEach((snapshot, index) => {
        const marker = BABYLON.MeshBuilder.CreateSphere('marker_' + index, { diameter: 0.25 }, scene);
        marker.position = snapshot.position.clone();

        const material = new BABYLON.StandardMaterial('markerMat_' + index, scene);
        material.diffuseColor = new BABYLON.Color3(0.86, 0.15, 0.15);
        material.emissiveColor = new BABYLON.Color3(0.86, 0.15, 0.15);
        material.disableLighting = true;
        marker.material = material;
        marker.snapshotName = snapshot.name;
        marker.snapshotIndex = index;

        markers.push(marker);
    });

    document.getElementById('defectCount').textContent = markers.length;
    document.getElementById('defectStat').textContent = markers.length;
}

function updateMarkerColors() {
    markers.forEach((marker, index) => {
        if (index < defectsData.length) {
            const defect = defectsData[index];
            if (marker && marker.material) {
                marker.material.diffuseColor = getSeverityColor(defect.severity);
                marker.material.emissiveColor = getSeverityColor(defect.severity);
            }
            marker.defectId = defect.defectId;
            marker.severity = defect.severity;
        }
    });
}

function renderDefectMarkers(defects) {
    if (markers.length > 0) {
        markers.forEach(m => {
            if (m) m.dispose();
        });
        markers = [];
    }

    // Create markers from database coordinates, fallback to baked snapshots
    defects.forEach((defect, index) => {
        let posX = defect.x;
        let posY = defect.y;
        let posZ = defect.z;

        // Fallback if coordinates are perfectly zero (legacy DB entries without GLB extraction)
        if (posX === 0 && posY === 0 && posZ === 0 && index < snapshotMeshes.length) {
            posX = snapshotMeshes[index].position.x;
            posY = snapshotMeshes[index].position.y;
            posZ = snapshotMeshes[index].position.z;
        }

        const marker = BABYLON.MeshBuilder.CreateSphere('marker' + defect.defectId, { diameter: 0.35 }, scene);
        marker.position = new BABYLON.Vector3(posX, posY, posZ);

        const material = new BABYLON.StandardMaterial('mat' + defect.defectId, scene);
        material.diffuseColor = getSeverityColor(defect.severity);
        material.emissiveColor = getSeverityColor(defect.severity);
        material.disableLighting = true;
        marker.material = material;
        marker.defectId = defect.defectId;
        marker.severity = defect.severity;

        markers.push(marker);
    });
}

function getStatusColor(status) {
    switch (status) {
        case 'Reported': return new BABYLON.Color3(0.86, 0.15, 0.15);
        case 'Under Review': return new BABYLON.Color3(0.96, 0.62, 0.04);
        case 'Fixed': return new BABYLON.Color3(0.13, 0.77, 0.35);
        default: return new BABYLON.Color3(0.5, 0.5, 0.5);
    }
}

function getSeverityColor(severity) {
    switch (severity) {
        case 'Low': return new BABYLON.Color3(0.13, 0.77, 0.35);  // Green
        case 'Medium': return new BABYLON.Color3(0.96, 0.62, 0.04);  // Yellow/Orange
        case 'High': return new BABYLON.Color3(0.98, 0.45, 0.09);  // Orange
        case 'Critical': return new BABYLON.Color3(0.94, 0.27, 0.27);  // Red
        default: return new BABYLON.Color3(0.96, 0.62, 0.04);  // Default to yellow
    }
}

// Click handler for markers and adding defects
scene.onPointerObservable.add((pointerInfo) => {
    const pickResult = scene.pick(pointerInfo.event.clientX, pointerInfo.event.clientY);
    if (pointerInfo.type === BABYLON.PointerEventTypes.POINTERDOWN) {
        if (isAddMode) {
            if (pickResult.hit && pickResult.pickedMesh && !pickResult.pickedMesh.name.startsWith('marker') && pickResult.pickedMesh.name !== 'ghostMarker') {
                openNewDefectModal(pickResult.pickedPoint);
                toggleAddMode();
            }
        } else if (pickResult.hit && pickResult.pickedMesh && pickResult.pickedMesh.name.startsWith('marker')) {
            const defectId = pickResult.pickedMesh.defectId;
            const snapshotIndex = pickResult.pickedMesh.snapshotIndex;
            if (defectId) {
                openDefectModal(defectId);
            } else if (snapshotIndex !== undefined && snapshotIndex < defectsData.length) {
                openDefectModal(defectsData[snapshotIndex].defectId);
            }
        }
    } else if (pointerInfo.type === BABYLON.PointerEventTypes.POINTERMOVE) {
        if (isAddMode && ghostMarker) {
            if (pickResult.hit && pickResult.pickedMesh && !pickResult.pickedMesh.name.startsWith('marker') && pickResult.pickedMesh.name !== 'ghostMarker') {
                ghostMarker.position = pickResult.pickedPoint;
                ghostMarker.isVisible = true;
            } else {
                ghostMarker.isVisible = false;
            }
        }
    }
});

function selectDefect(defectId) {
    document.querySelectorAll('.defect-card').forEach(c => c.classList.remove('selected', 'expanded'));
    const card = document.querySelector(`.defect-card[data-id="${defectId}"]`);
    if (card) {
        card.classList.add('selected', 'expanded');
        loadDefectDetails(defectId);
        card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
}

function focusDefect(defectId) {
    const defectIndex = defectsData.findIndex(d => d.defectId === defectId);
    if (defectIndex >= 0 && defectIndex < markers.length) {
        const marker = markers[defectIndex];
        camera.target = marker.position.clone();
        camera.radius = 3;
    } else {
        const defect = defectsData.find(d => d.defectId === defectId);
        if (defect) {
            camera.target = new BABYLON.Vector3(defect.x, defect.y, defect.z);
            camera.radius = 3;
        }
    }
    selectDefect(defectId);
}

function openDefectModal(defectId) {
    currentDefectId = defectId;
    document.getElementById('defectModal').querySelector('h3').innerHTML = '<i class="fas fa-edit"></i> Edit Defect';
    document.getElementById('defectDesc').readOnly = true;

    fetch(`/module3/api/defects/${defectId}`)
        .then(response => response.json())
        .then(data => {
            document.getElementById('defectElement').value = data.element || 'Unknown';
            document.getElementById('defectLocation').value = data.location || '';
            document.getElementById('defectType').value = data.defect_type || 'Unknown';
            document.getElementById('defectSeverity').value = data.severity || 'Medium';
            document.getElementById('defectDesc').value = data.description || '';
            document.getElementById('defectCoords').value = `X: ${data.x}, Y: ${data.y}, Z: ${data.z}`;
            document.getElementById('defectStatus').value = data.status;
            document.getElementById('defectNotes').value = data.notes || '';

            const imgInput = document.getElementById('defectImageInput');
            if (imgInput) imgInput.value = '';

            if (data.imageUrl) {
                document.getElementById('defectImage').src = data.imageUrl;
                document.getElementById('defectImage').style.display = 'block';
            } else {
                document.getElementById('defectImage').style.display = 'none';
            }
            document.getElementById('defectModal').classList.add('active');
        });
}

function closeModal() {
    document.getElementById('defectModal').classList.remove('active');
    currentDefectId = null;
}

function toggleAddMode() {
    isAddMode = !isAddMode;
    const btn = document.getElementById('addDefectBtn');
    if (isAddMode) {
        btn.classList.add('active');
        document.getElementById('renderCanvas').style.cursor = 'crosshair';

        if (!ghostMarker) {
            ghostMarker = BABYLON.MeshBuilder.CreateSphere('ghostMarker', { diameter: 0.25 }, scene);
            const mat = new BABYLON.StandardMaterial('ghostMat', scene);
            mat.diffuseColor = new BABYLON.Color3(1, 0, 0);
            mat.alpha = 0.5;
            ghostMarker.material = mat;
        }
        ghostMarker.isVisible = false;
    } else {
        btn.classList.remove('active');
        document.getElementById('renderCanvas').style.cursor = 'default';
        if (ghostMarker) ghostMarker.isVisible = false;
    }
}

function openNewDefectModal(point) {
    currentDefectId = null;
    document.getElementById('defectModal').querySelector('h3').innerHTML = '<i class="fas fa-plus-circle"></i> Add New Defect';
    document.getElementById('defectElement').value = '3D Pin';
    document.getElementById('defectLocation').value = '';
    document.getElementById('defectType').value = 'Unknown';
    document.getElementById('defectSeverity').value = 'Medium';

    const descEl = document.getElementById('defectDesc');
    descEl.value = '';
    descEl.readOnly = false;

    document.getElementById('defectCoords').value = `X: ${point.x.toFixed(2)}, Y: ${point.y.toFixed(2)}, Z: ${point.z.toFixed(2)}`;
    document.getElementById('defectCoords').dataset.x = point.x;
    document.getElementById('defectCoords').dataset.y = point.y;
    document.getElementById('defectCoords').dataset.z = point.z;

    document.getElementById('defectStatus').value = 'Reported';
    document.getElementById('defectNotes').value = '';

    const imgInput = document.getElementById('defectImageInput');
    if (imgInput) imgInput.value = '';

    document.getElementById('defectImage').style.display = 'none';

    document.getElementById('defectModal').classList.add('active');
}

function saveDefect() {
    const location = document.getElementById('defectLocation').value;
    const defect_type = document.getElementById('defectType').value;
    const severity = document.getElementById('defectSeverity').value;
    const status = document.getElementById('defectStatus').value;
    const notes = document.getElementById('defectNotes').value;
    const description = document.getElementById('defectDesc').value;

    const formData = new FormData();
    if (location) formData.append('location', location);
    formData.append('defect_type', defect_type);
    formData.append('severity', severity);
    formData.append('status', status);
    formData.append('notes', notes);
    formData.append('description', description);

    const fileInput = document.getElementById('defectImageInput');
    if (fileInput && fileInput.files.length > 0) {
        for (let i = 0; i < fileInput.files.length; i++) {
            formData.append('images', fileInput.files[i]);
        }
    }

    if (currentDefectId) {
        fetch(`/module3/api/defects/${currentDefectId}`, {
            method: 'PUT',
            body: formData
        })
            .then(response => response.json())
            .then(() => {
                closeModal();
                loadDefects();
            });
    } else {
        const coords = document.getElementById('defectCoords').dataset;
        formData.append('x', parseFloat(coords.x));
        formData.append('y', parseFloat(coords.y));
        formData.append('z', parseFloat(coords.z));

        fetch('/module3/api/scans/' + window.APP_CONFIG.scanId + '/defects', {
            method: 'POST',
            body: formData
        })
            .then(response => response.json())
            .then(() => {
                closeModal();
                loadDefects();
            });
    }
}

function deleteDefect(defectId) {
    if (confirm('Are you sure you want to delete this defect?')) {
        fetch(`/module3/api/defects/${defectId}`, { method: 'DELETE' })
            .then(response => response.json())
            .then(() => loadDefects());
    }
}

// View controls
function resetView() {
    camera.alpha = -Math.PI / 2;
    camera.beta = Math.PI / 2.5;
    if (modelBounds.size) {
        camera.radius = modelBounds.size.length() * 1.5;
        camera.target = modelCenter;
    } else {
        camera.radius = 20;
        camera.target = BABYLON.Vector3.Zero();
    }
}

function setTopView() {
    camera.alpha = 0;
    camera.beta = 0.01;
    camera.target = modelCenter;
}

function setFrontView() {
    camera.alpha = -Math.PI / 2;
    camera.beta = Math.PI / 2;
    camera.target = modelCenter;
}

function set3DView() {
    camera.alpha = -Math.PI / 4;
    camera.beta = Math.PI / 3;
    camera.target = modelCenter;
}

function zoomIn() {
    camera.radius = Math.max(1, camera.radius * 0.8);
}

function zoomOut() {
    camera.radius = camera.radius * 1.25;
}

function fitToView() {
    if (modelBounds.size) {
        camera.target = modelCenter;
        camera.radius = modelBounds.size.length() * 1.2;
    }
}

function toggleDefects() {
    defectsVisible = !defectsVisible;
    markers.forEach(m => m.isVisible = defectsVisible);
    document.getElementById('toggleDefectsBtn').classList.toggle('active', defectsVisible);
}

function toggleXRay() {
    xrayMode = !xrayMode;
    loadedMeshes.forEach(mesh => {
        if (mesh.material && !mesh.name.startsWith('marker') && !mesh.name.toLowerCase().includes('snapshot')) {
            if (xrayMode) {
                // High transparency for X-ray mode (0.15 = 85% transparent)
                mesh.material.alpha = 0.15;
                // Disable backface culling to see through objects
                mesh.material.backFaceCulling = false;
            } else {
                // Restore original alpha or default to 1
                mesh.material.alpha = mesh.material.originalAlpha || 1.0;
                // Re-enable backface culling
                mesh.material.backFaceCulling = true;
            }
        }
    });
    document.getElementById('xrayBtn').classList.toggle('active', xrayMode);
}

function toggleWireframe() {
    wireframeMode = !wireframeMode;
    loadedMeshes.forEach(mesh => {
        if (mesh.material && !mesh.name.startsWith('marker')) {
            mesh.material.wireframe = wireframeMode;
        }
    });
    document.getElementById('wireframeBtn').classList.toggle('active', wireframeMode);
}

function toggleDebugInspector() {
    if (scene.debugLayer.isVisible()) {
        scene.debugLayer.hide();
    } else {
        scene.debugLayer.show();
    }
}

// Theme toggle
function toggleTheme() {
    const body = document.body;
    const themeIcon = document.getElementById('themeIcon');

    body.classList.toggle('light-mode');
    const isLight = body.classList.contains('light-mode');

    // Update icon
    if (isLight) {
        themeIcon.className = 'fas fa-sun';
        // Light mode 3D scene background
        scene.clearColor = new BABYLON.Color4(0.89, 0.91, 0.94, 1);
    } else {
        themeIcon.className = 'fas fa-moon';
        // Dark mode 3D scene background
        scene.clearColor = new BABYLON.Color4(0.04, 0.06, 0.10, 1);
    }

    // Save preference
    localStorage.setItem('theme', isLight ? 'light' : 'dark');
}

// Load saved theme on page load
document.addEventListener('DOMContentLoaded', () => {
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'light') {
        document.body.classList.add('light-mode');
        document.getElementById('themeIcon').className = 'fas fa-sun';
        if (typeof scene !== 'undefined') {
            scene.clearColor = new BABYLON.Color4(0.89, 0.91, 0.94, 1);
        }
    }
});

// Update camera info
scene.registerBeforeRender(() => {
    const pos = camera.position;
    document.getElementById('cameraInfo').innerHTML =
        `<i class="fas fa-video"></i> X:${pos.x.toFixed(1)} Y:${pos.y.toFixed(1)} Z:${pos.z.toFixed(1)} | Zoom: ${camera.radius.toFixed(1)}`;
});

// Render loop
engine.runRenderLoop(() => {
    scene.render();
});

window.addEventListener('resize', () => {
    engine.resize();
});

// Initial load - only if no model URL
if (!window.APP_CONFIG.modelUrl) {
    loadDefects();
}
