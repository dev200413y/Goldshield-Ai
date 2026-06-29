/**
 * GoldShield AI — 3D Jewelry Model Viewer (Three.js)
 * True Image-to-3D integration (GLB/GLTF loading)
 */

class GoldShield3DViewer {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        if (!this.container) return;

        this.width = this.container.clientWidth || 300;
        this.height = this.container.clientHeight || 300;

        // Scene
        this.scene = new THREE.Scene();
        
        // Dark luxurious background matching dashboard
        this.scene.background = new THREE.Color(0x0f1115);
        this.scene.fog = new THREE.Fog(0x0f1115, 10, 50);

        // Camera
        this.camera = new THREE.PerspectiveCamera(45, this.width / this.height, 0.1, 100);
        this.camera.position.set(0, 5, 12);

        // Renderer
        this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
        this.renderer.setSize(this.width, this.height);
        this.renderer.setPixelRatio(window.devicePixelRatio);
        this.renderer.outputEncoding = THREE.sRGBEncoding;
        this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
        this.renderer.toneMappingExposure = 1.2;
        this.container.appendChild(this.renderer.domElement);

        // Controls
        this.controls = new THREE.OrbitControls(this.camera, this.renderer.domElement);
        this.controls.enableDamping = true;
        this.controls.dampingFactor = 0.05;
        this.controls.autoRotate = true;
        this.controls.autoRotateSpeed = 2.0;
        this.controls.maxPolarAngle = Math.PI / 1.5; // Don't go below ground
        this.controls.minDistance = 2;
        this.controls.maxDistance = 20;

        // Lighting (crucial for PBR gold)
        this._setupLighting();

        // Environment map (simulated reflection for gold)
        this._setupEnvironment();

        // Floor Grid
        this._addGrid();

        // Group to hold the loaded or generated model
        this.jewelryGroup = new THREE.Group();
        this.scene.add(this.jewelryGroup);

        // Base plate (scale)
        this._addBasePlate();

        // Animation Loop
        this.animate = this.animate.bind(this);
        this.animate();

        // Resize handler
        window.addEventListener('resize', this._onWindowResize.bind(this));
    }

    _setupLighting() {
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.4);
        this.scene.add(ambientLight);

        const dirLight = new THREE.DirectionalLight(0xfff5e6, 2.5); // Warm light
        dirLight.position.set(5, 10, 7);
        this.scene.add(dirLight);

        const fillLight = new THREE.DirectionalLight(0xe6f0ff, 1.0); // Cool fill
        fillLight.position.set(-5, 5, -5);
        this.scene.add(fillLight);
        
        const rimLight = new THREE.PointLight(0xffd700, 2, 20); // Golden rim light
        rimLight.position.set(0, 3, -5);
        this.scene.add(rimLight);
    }

    _setupEnvironment() {
        // Create a simple environment map using a canvas for realistic reflections
        const envCanvas = document.createElement('canvas');
        envCanvas.width = 1024;
        envCanvas.height = 512;
        const ctx = envCanvas.getContext('2d');
        
        // Complex gradient for a studio look (simulating softboxes)
        const grad = ctx.createLinearGradient(0, 0, 0, 512);
        grad.addColorStop(0, '#111111');
        grad.addColorStop(0.4, '#ffffff'); // Strong horizontal light
        grad.addColorStop(0.5, '#444444');
        grad.addColorStop(0.6, '#ffffff'); // Strong horizontal light
        grad.addColorStop(1, '#050505');
        ctx.fillStyle = grad;
        ctx.fillRect(0, 0, 1024, 512);
        
        // Add a "window" reflection
        ctx.fillStyle = '#ffffff';
        ctx.fillRect(200, 200, 100, 100);
        ctx.fillRect(700, 250, 150, 50);

        const envTexture = new THREE.CanvasTexture(envCanvas);
        envTexture.mapping = THREE.EquirectangularReflectionMapping;
        this.scene.environment = envTexture;
    }

    _addGrid() {
        const gridHelper = new THREE.GridHelper(20, 20, 0x444444, 0x222222);
        gridHelper.position.y = -2;
        this.scene.add(gridHelper);
    }

    _addBasePlate() {
        const plateGeo = new THREE.CylinderGeometry(4, 4, 0.2, 32);
        const plateMat = new THREE.MeshStandardMaterial({
            color: 0x111318,
            metalness: 0.8,
            roughness: 0.4
        });
        const plate = new THREE.Mesh(plateGeo, plateMat);
        plate.position.y = -1.9;
        this.scene.add(plate);

        // Add "GoldShield Scanner" text conceptually by adding a colored ring
        const ringGeo = new THREE.TorusGeometry(3.9, 0.05, 16, 64);
        const ringMat = new THREE.MeshStandardMaterial({
            color: 0x60a5fa, // scanner blue
            emissive: 0x2563eb,
            emissiveIntensity: 0.5
        });
        const scannerRing = new THREE.Mesh(ringGeo, ringMat);
        scannerRing.position.y = -1.8;
        scannerRing.rotation.x = Math.PI / 2;
        this.scene.add(scannerRing);
    }

    _clearModel() {
        while (this.jewelryGroup.children.length > 0) {
            const child = this.jewelryGroup.children[0];
            if (child.geometry) child.geometry.dispose();
            if (child.material) {
                if (Array.isArray(child.material)) {
                    child.material.forEach(m => m.dispose());
                } else {
                    child.material.dispose();
                }
            }
            this.jewelryGroup.remove(child);
        }
    }

    // High quality Gold Material
    _getGoldMaterial() {
        // Create a procedural noise texture for micro-scratches/bump
        const canvas = document.createElement('canvas');
        canvas.width = 256;
        canvas.height = 256;
        const context = canvas.getContext('2d');
        for (let i = 0; i < 256; i++) {
            for (let j = 0; j < 256; j++) {
                const val = Math.floor(Math.random() * 255);
                context.fillStyle = `rgb(${val},${val},${val})`;
                context.fillRect(i, j, 1, 1);
            }
        }
        const bumpTexture = new THREE.CanvasTexture(canvas);
        bumpTexture.wrapS = THREE.RepeatWrapping;
        bumpTexture.wrapT = THREE.RepeatWrapping;
        bumpTexture.repeat.set(10, 10);

        return new THREE.MeshPhysicalMaterial({
            color: 0xffd700,         // Base gold color
            metalness: 1.0,          // Fully metallic
            roughness: 0.2,          // Slightly rough for realism
            bumpMap: bumpTexture,
            bumpScale: 0.002,        // Subtle micro-scratches
            envMapIntensity: 2.0,    // Strong reflections
            clearcoat: 0.3,
            clearcoatRoughness: 0.2,
            reflectivity: 1.0
        });
    }

    /**
     * Load an actual AI-generated 3D model (.glb/.gltf)
     * Fallback to a procedural realistic shape if URL is empty.
     */
    loadGenerativeModel(itemType, modelUrl) {
        this._clearModel();
        
        if (modelUrl && typeof THREE.GLTFLoader !== 'undefined') {
            const loader = new THREE.GLTFLoader();
            loader.load(
                modelUrl,
                (gltf) => {
                    const model = gltf.scene;
                    
                    // Center and scale the model
                    const box = new THREE.Box3().setFromObject(model);
                    const center = box.getCenter(new THREE.Vector3());
                    const size = box.getSize(new THREE.Vector3());
                    
                    const maxDim = Math.max(size.x, size.y, size.z);
                    const scale = 5.0 / maxDim; // Normalize scale to fit nicely in view
                    
                    model.scale.set(scale, scale, scale);
                    model.position.set(-center.x * scale, -center.y * scale, -center.z * scale);
                    
                    // Apply luxurious gold material to all meshes in the loaded model
                    model.traverse((child) => {
                        if (child.isMesh) {
                            child.material = this._getGoldMaterial();
                        }
                    });
                    
                    // Wrap in an outer group to keep it centered during rotation
                    const wrapper = new THREE.Group();
                    wrapper.add(model);
                    this.jewelryGroup.add(wrapper);
                },
                (xhr) => {
                    console.log((xhr.loaded / xhr.total * 100) + '% loaded');
                },
                (error) => {
                    console.error('Error loading GLB, falling back to procedural:', error);
                    this._createProceduralModel(itemType);
                }
            );
        } else {
            // Fallback: If no URL provided (or Tripo API key missing), generate an incredibly realistic procedural gold object
            this._createProceduralModel(itemType);
        }
    }

    _createProceduralModel(itemType) {
        const material = this._getGoldMaterial();
        let geometry;
        let scale = 1;

        switch (itemType) {
            case 'bangle':
            case 'bracelet':
                geometry = new THREE.TorusGeometry(3, 0.4, 64, 100);
                geometry.rotateX(Math.PI / 2);
                break;
            case 'chain':
                geometry = new THREE.TorusKnotGeometry(2, 0.3, 200, 32);
                break;
            case 'coin':
                geometry = new THREE.CylinderGeometry(2, 2, 0.2, 64);
                geometry.rotateX(Math.PI / 2);
                break;
            case 'bar':
                geometry = new THREE.BoxGeometry(2, 4, 0.4);
                break;
            case 'ring':
            default:
                // Create a very detailed procedural ring (Torus with an inset)
                geometry = new THREE.TorusGeometry(2, 0.6, 64, 100);
                geometry.rotateX(Math.PI / 2);
                break;
        }

        const mesh = new THREE.Mesh(geometry, material);
        mesh.scale.set(scale, scale, scale);
        
        // Add some "diamonds" or details if it's a ring
        if (itemType === 'ring' || itemType === 'pendant') {
            const detailGeo = new THREE.OctahedronGeometry(0.8, 2);
            const detailMat = new THREE.MeshStandardMaterial({
                color: 0xffffff,
                metalness: 0.1,
                roughness: 0.05,
                transmission: 0.9,
                ior: 2.4, // Diamond IOR
                thickness: 0.5
            });
            const detailMesh = new THREE.Mesh(detailGeo, detailMat);
            detailMesh.position.y = 2.4;
            this.jewelryGroup.add(detailMesh);
        }

        this.jewelryGroup.add(mesh);
    }

    animate() {
        requestAnimationFrame(this.animate);
        if (this.controls) this.controls.update();
        if (this.renderer && this.scene && this.camera) {
            this.renderer.render(this.scene, this.camera);
        }
    }

    _onWindowResize() {
        if (!this.container) return;
        this.width = this.container.clientWidth;
        this.height = this.container.clientHeight;
        this.camera.aspect = this.width / this.height;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(this.width, this.height);
    }

    resetView() {
        this.camera.position.set(0, 5, 12);
        this.controls.target.set(0, 0, 0);
        this.controls.update();
    }

    toggleRotation() {
        this.controls.autoRotate = !this.controls.autoRotate;
        return this.controls.autoRotate;
    }

    dispose() {
        if (this.renderer) {
            this.renderer.dispose();
            if (this.container && this.container.contains(this.renderer.domElement)) {
                this.container.removeChild(this.renderer.domElement);
            }
        }
        if (this.controls) this.controls.dispose();
        
        // Traverse the scene and dispose all geometries and materials to avoid memory leaks
        if (this.scene) {
            this.scene.traverse((object) => {
                if (!object.isMesh) return;
                
                if (object.geometry) {
                    object.geometry.dispose();
                }
                
                if (object.material) {
                    if (Array.isArray(object.material)) {
                        object.material.forEach(material => material.dispose());
                    } else {
                        object.material.dispose();
                    }
                }
            });
        }
        
        // Remove window resize event listener
        window.removeEventListener('resize', this._onWindowResize.bind(this));
        
        // Stop animation loop by removing references
        this.renderer = null;
        this.scene = null;
        this.camera = null;
        this.controls = null;
    }
}
