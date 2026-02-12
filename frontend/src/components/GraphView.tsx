import React, { useEffect, useState, useRef, useCallback } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import ForceGraph3D from 'react-force-graph-3d';
import axios from 'axios';

interface GraphData {
    nodes: any[];
    links: any[];
}

const GraphView: React.FC = () => {
    const [data, setData] = useState<GraphData>({ nodes: [], links: [] });
    const [hoverNode, setHoverNode] = useState<any>(null);
    const [message, setMessage] = useState<string>('');
    const [isPaused, setIsPaused] = useState<boolean>(false);
    const [searchQuery, setSearchQuery] = useState<string>('');
    const [searchResults, setSearchResults] = useState<any[]>([]);
    const [askQuery, setAskQuery] = useState<string>('');
    const [askAnswer, setAskAnswer] = useState<any>(null);
    const [isAsking, setIsAsking] = useState<boolean>(false);
    const [hoverGoBtn, setHoverGoBtn] = useState<boolean>(false);
    const [hoverAskBtn, setHoverAskBtn] = useState<boolean>(false);
    const [vizType, setVizType] = useState<string>('2d'); // '2d', '3d', 'radial', 'tree'
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const fgRef = useRef<any>();

    const fetchData = async () => {
        try {
            const res = await axios.get('http://127.0.0.1:8000/graph');
            setData(res.data);
        } catch (error) {
            console.error("Error fetching graph data:", error);
        }
    };

    const handleSearch = async () => {
        if (!searchQuery.trim()) return;
        
        try {
            const res = await axios.post('http://127.0.0.1:8000/search', {
                query: searchQuery,
                top_k: 5
            });
            setSearchResults(res.data.results);
        } catch (error) {
            console.error("Search failed:", error);
            showMessage("✗ SEARCH FAILED");
        }
    };

    const handleAsk = async () => {
        if (!askQuery.trim()) return;
        
        setIsAsking(true);
        try {
            const res = await axios.post('http://127.0.0.1:8000/ask', {
                query: askQuery
            });
            setAskAnswer(res.data);
            showMessage("✓ ANSWER GENERATED");
        } catch (error) {
            console.error("Ask failed:", error);
            showMessage("✗ RAG QUERY FAILED");
        } finally {
            setIsAsking(false);
        }
    };

    const showMessage = (msg: string) => {
        setMessage(msg);
        setTimeout(() => setMessage(''), 3000);
    };

    const handleOpenFile = (filepath: string) => {
        if (filepath) {
            // Call backend to open file in OS default application
            axios.post('http://127.0.0.1:8000/open-file', { filepath })
                .then(response => {
                    if (response.data.success) {
                        showMessage(`> OPENING: ${filepath.split(/[\\\\/]/).pop()}`);
                    } else {
                        showMessage(`✗ ERROR: ${response.data.error}`);
                    }
                })
                .catch(error => {
                    console.error("Failed to open file:", error);
                    showMessage("✗ FAILED TO OPEN FILE");
                });
        }
    };

    useEffect(() => {
        fetchData();
        const interval = setInterval(() => {
            if (!isPaused) {
                fetchData();
            }
        }, 3000);
        return () => clearInterval(interval);
    }, [isPaused]);

    useEffect(() => {
        // Configure d3 forces based on visualization type
        if (fgRef.current && fgRef.current.d3Force) {
            if (vizType === 'radial') {
                fgRef.current.d3Force('charge').strength(-150);
                fgRef.current.d3Force('link').distance(120);
                fgRef.current.resumeAnimation?.();
                fgRef.current.d3ReheatSimulation?.();
            } else if (vizType === 'tree') {
                // Tree: completely disable forces, use fixed positions only
                fgRef.current.d3Force('charge').strength(0);
                fgRef.current.d3Force('link').strength(0);
                fgRef.current.d3Force('center').strength(0);
                // Stop simulation immediately
                fgRef.current.d3ReheatSimulation?.();
            } else {
                fgRef.current.d3Force('charge').strength(-200);
                fgRef.current.d3Force('link').distance(100);
                fgRef.current.resumeAnimation?.();
                fgRef.current.d3ReheatSimulation?.();
            }
        }
    }, [vizType, data]);

    useEffect(() => {
        if (vizType === '3d' && fgRef.current) {
            setTimeout(() => {
                fgRef.current.zoomToFit?.(400, 40);
            }, 100);
        }
    }, [vizType, data]);

    const handleNodeDrag = useCallback((node: any) => {
        if (node.group === 'file') {
            setIsPaused(true);
            // Don't fix position during drag for smoother movement
            // node.fx = node.x;
            // node.fy = node.y;
        }
    }, []);

    const handleNodeDragEnd = useCallback(async (node: any) => {
        setTimeout(() => setIsPaused(false), 500);
        
        if (node.group !== 'file') {
            return;
        }
        
        // Fix position temporarily to check cluster assignment
        node.fx = node.x;
        node.fy = node.y;
        
        let closestTopic = null;
        let minDist = Infinity;
        
        data.nodes.forEach(n => {
            if (n.group === 'topic') {
                const dx = (n.x || 0) - (node.x || 0);
                const dy = (n.y || 0) - (node.y || 0);
                const dist = Math.sqrt(dx * dx + dy * dy);
                if (dist < minDist) {
                    minDist = dist;
                    closestTopic = n.id;
                }
            }
        });
        
        node.fx = undefined;
        node.fy = undefined;
        
        if (closestTopic && node.filepath) {
            try {
                showMessage(`⚡ MOVING ${node.label} TO ${closestTopic}...`);
                await axios.post('http://127.0.0.1:8000/move-file', {
                    filepath: node.filepath,
                    target_cluster: closestTopic
                });
                await fetchData();
                showMessage(`✓ FILE RELOCATED TO ${closestTopic}`);
            } catch (error) {
                console.error('Failed to move file:', error);
                showMessage(`✗ TRANSFER FAILED`);
            }
        }
    }, [data.nodes]);

    // Prepare graph data based on visualization type
    const getLayoutData = () => {
        if (vizType === 'radial') {
            // Radial layout: arrange nodes in circles around root
            const layoutData = { ...data };
            const centerNode = data.nodes.find(n => n.group === 'root');
            if (centerNode) {
                centerNode.fx = 0;
                centerNode.fy = 0;
            }
            return layoutData;
        } else if (vizType === 'tree') {
            // Tree layout: basic top-down rows (root -> topics -> files)
            const layoutData = JSON.parse(JSON.stringify(data)); // Deep copy

            const rootNode = layoutData.nodes.find((n: any) => n.group === 'root');
            const topicNodes = layoutData.nodes.filter((n: any) => n.group === 'topic');
            const fileNodes = layoutData.nodes.filter((n: any) => n.group === 'file');

            const nodeById = new Map(layoutData.nodes.map((n: any) => [n.id, n]));
            const topicToFiles = new Map<string, any[]>();

            // Map files to topics regardless of link direction
            layoutData.links.forEach((link: any) => {
                const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
                const targetId = typeof link.target === 'object' ? link.target.id : link.target;
                const sourceNode = nodeById.get(sourceId);
                const targetNode = nodeById.get(targetId);

                if (!sourceNode || !targetNode) return;

                if (sourceNode.group === 'topic' && targetNode.group === 'file') {
                    if (!topicToFiles.has(sourceNode.id)) topicToFiles.set(sourceNode.id, []);
                    topicToFiles.get(sourceNode.id)!.push(targetNode);
                } else if (targetNode.group === 'topic' && sourceNode.group === 'file') {
                    if (!topicToFiles.has(targetNode.id)) topicToFiles.set(targetNode.id, []);
                    topicToFiles.get(targetNode.id)!.push(sourceNode);
                }
            });

            const canvasWidth = Math.max(600, window.innerWidth - 400);
            const canvasHeight = Math.max(600, window.innerHeight);
            const left = -canvasWidth / 2 + 80;
            const right = canvasWidth / 2 - 80;
            const rootY = -canvasHeight / 2 + 90;
            const topicY = rootY + 170;
            const fileY = topicY + 180;

            // Root centered at top
            if (rootNode) {
                rootNode.fx = 0;
                rootNode.fy = rootY;
            }

            // Topics row
            const topicCount = Math.max(1, topicNodes.length);
            const topicSpan = right - left;
            const topicStep = topicCount === 1 ? 0 : topicSpan / (topicCount - 1);
            topicNodes.forEach((topic: any, i: number) => {
                topic.fx = left + (topicStep * i);
                topic.fy = topicY;
            });

            // Files row per topic (simple horizontal spread)
            topicNodes.forEach((topic: any) => {
                const files = topicToFiles.get(topic.id) || [];
                const fileSpacing = 80;
                const totalWidth = (files.length - 1) * fileSpacing;
                files.forEach((fileNode: any, i: number) => {
                    fileNode.fx = topic.fx + (i * fileSpacing) - (totalWidth / 2);
                    fileNode.fy = fileY;
                });
            });

            // Any unassigned files fall back to center
            fileNodes.forEach((node: any) => {
                if (node.fx === undefined || node.fy === undefined) {
                    node.fx = 0;
                    node.fy = fileY;
                }
            });

            return layoutData;
        }
        return data;
    };

    const renderGraph = () => {
        const layoutData = getLayoutData();
        const commonProps = {
            ref: fgRef,
            graphData: layoutData,
            nodeLabel: (node: any) => `<div style="color: #00ff00; font-family: SF Mono, Monaco, Consolas, monospace; background: #000; padding: 5px; border: 1px solid #00ff00;">${node.label}</div>`,
            linkColor: () => '#00ff00',
            linkWidth: 1,
            enableNodeDrag: vizType !== 'tree',
            onNodeDrag: vizType !== 'tree' ? handleNodeDrag : undefined,
            onNodeDragEnd: vizType !== 'tree' ? handleNodeDragEnd : undefined,
            onNodeHover: (node: any) => {
                setHoverNode(node);
                if (node && node.group === 'file' && vizType !== 'tree') {
                    document.body.style.cursor = 'grab';
                } else {
                    document.body.style.cursor = 'default';
                }
            },
            onNodeClick: (node: any) => {
                if (node?.group === 'file' && node.filepath && vizType !== 'tree') {
                    showMessage(`> DRAG FILE TO RELOCATE`);
                }
            }
        };

        if (vizType === '3d') {
            return (
                <ForceGraph3D
                    key={`fg-3d-${data.nodes.length}-${data.links.length}`}
                    {...commonProps}
                    width={window.innerWidth - 400}
                    height={window.innerHeight}
                    backgroundColor="#000000"
                    nodeColor={(node: any) => {
                        if (node.group === 'topic') return '#00ff00';
                        if (node.group === 'root') return '#00ff00';
                        return '#00aa00';
                    }}
                    nodeOpacity={0.9}
                    nodeResolution={16}
                    linkOpacity={0.3}
                    d3VelocityDecay={0.15}
                    d3AlphaDecay={0.04}
                    cooldownTime={1000}
                    warmupTicks={50}
                />
            );
        }

        // 2D, Radial, and Tree all use 2D rendering
        return (
            <ForceGraph2D
                key={`fg-2d-${vizType}-${data.nodes.length}-${data.links.length}`}
                {...commonProps}
                width={window.innerWidth - 400}
                height={window.innerHeight}
                backgroundColor="#000000"
                d3VelocityDecay={0.15}
                d3AlphaDecay={0.04}
                d3AlphaMin={0.001}
                cooldownTime={vizType === 'tree' ? 0 : 1000}
                warmupTicks={vizType === 'tree' ? 0 : 50}
                linkDirectionalParticles={0}
                nodeCanvasObject={(node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
                    const label = node.label as string;
                    const fontSize = 11 / globalScale;
                    ctx.font = `600 ${fontSize}px SF Mono, Monaco, Consolas, monospace`;

                    const isTree = vizType === 'tree';

                    if (node.group === 'topic') {
                        ctx.shadowBlur = 20;
                        ctx.shadowColor = '#00ff00';
                        
                        if (isTree) {
                            // Tree: Draw boxes for topics
                            ctx.fillStyle = 'rgba(0, 255, 0, 0.1)';
                            ctx.fillRect(node.x! - 40, node.y! - 25, 80, 50);
                            ctx.strokeStyle = '#00ff00';
                            ctx.lineWidth = 2;
                            ctx.strokeRect(node.x! - 40, node.y! - 25, 80, 50);
                            
                            ctx.shadowBlur = 0;
                            ctx.fillStyle = '#00ff00';
                            ctx.textAlign = 'center';
                            ctx.fillText(label, node.x!, node.y! + 4);
                        } else {
                            // 2D/Radial: Draw circles
                            ctx.fillStyle = 'rgba(0, 255, 0, 0.1)';
                            ctx.beginPath();
                            ctx.arc(node.x!, node.y!, 25, 0, 2 * Math.PI, false);
                            ctx.fill();

                            ctx.fillStyle = '#00ff00';
                            ctx.beginPath();
                            ctx.arc(node.x!, node.y!, 10, 0, 2 * Math.PI, false);
                            ctx.fill();

                            ctx.shadowBlur = 0;
                            ctx.fillStyle = '#00ff00';
                            ctx.fillText(label, node.x!, node.y! + 30);
                        }

                    } else if (node.group === 'root') {
                        ctx.shadowBlur = 30;
                        ctx.shadowColor = '#00ff00';
                        ctx.fillStyle = '#00ff00';
                        
                        if (isTree) {
                            // Tree: Draw square for root
                            ctx.fillRect(node.x! - 12, node.y! - 12, 24, 24);
                            ctx.strokeStyle = '#000';
                            ctx.lineWidth = 2;
                            ctx.strokeRect(node.x! - 12, node.y! - 12, 24, 24);
                        } else {
                            // 2D/Radial: Draw circle
                            ctx.beginPath();
                            ctx.arc(node.x!, node.y!, 8, 0, 2 * Math.PI, false);
                            ctx.fill();
                        }
                        ctx.shadowBlur = 0;
                    } else {
                        const isHovered = hoverNode?.id === node.id;
                        
                        if (isTree) {
                            // Tree: Draw boxes for file nodes
                            const boxWidth = 70;
                            const boxHeight = 20;
                            
                            if (isHovered) {
                                ctx.shadowBlur = 15;
                                ctx.shadowColor = '#00ff00';
                                ctx.fillStyle = 'rgba(0, 255, 0, 0.2)';
                                ctx.fillRect(node.x! - boxWidth/2 - 5, node.y! - boxHeight/2 - 5, boxWidth + 10, boxHeight + 10);
                            }
                            
                            ctx.shadowBlur = 10;
                            ctx.shadowColor = '#00ff00';
                            ctx.fillStyle = isHovered ? '#00ff00' : '#00aa00';
                            ctx.fillRect(node.x! - boxWidth/2, node.y! - boxHeight/2, boxWidth, boxHeight);
                            
                            ctx.strokeStyle = '#00ff00';
                            ctx.lineWidth = 1;
                            ctx.strokeRect(node.x! - boxWidth/2, node.y! - boxHeight/2, boxWidth, boxHeight);
                            
                            ctx.shadowBlur = 0;
                            ctx.fillStyle = isHovered ? '#000' : '#00ff00';
                            ctx.textAlign = 'center';
                            ctx.fillText(label, node.x!, node.y! + 4);
                        } else {
                            // 2D/Radial: Draw circles
                            if (isHovered) {
                                ctx.shadowBlur = 15;
                                ctx.shadowColor = '#00ff00';
                                ctx.fillStyle = 'rgba(0, 255, 0, 0.2)';
                                ctx.beginPath();
                                ctx.arc(node.x!, node.y!, 20, 0, 2 * Math.PI, false);
                                ctx.fill();
                            }
                            
                            ctx.shadowBlur = 10;
                            ctx.shadowColor = '#00ff00';
                            ctx.fillStyle = isHovered ? '#00ff00' : '#00aa00';
                            ctx.beginPath();
                            ctx.arc(node.x!, node.y!, 8, 0, 2 * Math.PI, false);
                            ctx.fill();
                            
                            ctx.shadowBlur = 0;
                            if (globalScale > 0.8 || isHovered) {
                                ctx.fillStyle = '#00ff00';
                                ctx.fillText(label, node.x! + 12, node.y! + 4);
                            }
                        }
                    }
                }}
            />
        );
    };

    return (
        <div style={{ 
            width: '100vw', 
            height: '100vh', 
            background: '#000000',
            fontFamily: 'SF Mono, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
            overflow: 'hidden',
            margin: 0,
            padding: 0,
            position: 'fixed',
            top: 0,
            left: 0
        }}>
            <div style={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                height: '100%',
                background: 'radial-gradient(ellipse at center, #001100 0%, #000000 100%)',
                opacity: 0.5,
                pointerEvents: 'none',
                zIndex: 0
            }}></div>

            {renderGraph()}
            
            <div style={{ 
                position: 'absolute', 
                top: 20, 
                left: 20, 
                color: '#00ff00', 
                fontFamily: 'SF Mono, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
                pointerEvents: 'none',
                textShadow: '0 0 10px #00ff00',
                zIndex: 100
            }}>
                <div style={{ fontSize: '1.8rem', fontWeight: 'bold', letterSpacing: '3px' }}>
                    &gt; SEMANTIC FILE SYSTEM
                </div>
                <div style={{ marginTop: '5px', opacity: 0.7, fontSize: '0.9rem' }}>
                    STATUS: <span style={{ color: '#00ff00', animation: 'blink 1s infinite' }}>ONLINE</span>
                </div>
            </div>

            {/* Visualization Type Switcher */}
            <div style={{ 
                position: 'absolute', 
                bottom: 90, 
                left: 20, 
                color: '#00ff00', 
                fontFamily: 'SF Mono, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
                fontSize: '0.75rem',
                textShadow: '0 0 5px #00ff00',
                zIndex: 100,
                pointerEvents: 'auto'
            }}>
                <div style={{ marginBottom: '8px', opacity: 0.7 }}>&gt; VISUALIZATION:</div>
                <div style={{ display: 'flex', gap: '5px', flexDirection: 'column' }}>
                    {['2d', '3d', 'radial', 'tree'].map(type => (
                        <button
                            key={type}
                            onClick={() => setVizType(type)}
                            style={{
                                background: vizType === type ? '#00ff00' : '#000',
                                border: '1px solid #00ff00',
                                color: vizType === type ? '#000' : '#00ff00',
                                padding: '5px 12px',
                                fontFamily: 'SF Mono, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
                                cursor: 'pointer',
                                fontSize: '0.7rem',
                                fontWeight: 'bold',
                                textTransform: 'uppercase',
                                transition: 'all 0.2s ease',
                                boxShadow: vizType === type ? '0 0 10px rgba(0, 255, 0, 0.5)' : 'none'
                            }}
                            onMouseEnter={(e) => {
                                if (vizType !== type) {
                                    e.currentTarget.style.background = 'rgba(0, 255, 0, 0.2)';
                                    e.currentTarget.style.boxShadow = '0 0 8px rgba(0, 255, 0, 0.3)';
                                }
                            }}
                            onMouseLeave={(e) => {
                                if (vizType !== type) {
                                    e.currentTarget.style.background = '#000';
                                    e.currentTarget.style.boxShadow = 'none';
                                }
                            }}
                        >
                            {type}
                        </button>
                    ))}
                </div>
            </div>

            <div style={{ 
                position: 'absolute', 
                bottom: 20, 
                left: 20, 
                color: '#00ff00', 
                fontFamily: 'SF Mono, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
                fontSize: '0.85rem',
                textShadow: '0 0 5px #00ff00',
                zIndex: 100
            }}>
                <div>&gt; NODES: {data.nodes.length}</div>
                <div>&gt; CLUSTERS: {data.nodes.filter(n => n.group === 'topic').length}</div>
                <div>&gt; FILES: {data.nodes.filter(n => n.group === 'file').length}</div>
            </div>

            {/* Right Sidebar */}
            <div style={{
                position: 'absolute',
                top: 0,
                right: 0,
                width: '400px',
                height: '100vh',
                background: 'rgba(0, 0, 0, 0.95)',
                borderLeft: '2px solid #00ff00',
                boxShadow: '-5px 0 30px rgba(0, 255, 0, 0.2)',
                display: 'flex',
                flexDirection: 'column',
                zIndex: 100
            }}>
                {/* Search Section */}
                <div style={{
                    flex: '1',
                    borderBottom: '2px solid #00ff00',
                    display: 'flex',
                    flexDirection: 'column',
                    overflow: 'hidden'
                }}>
                    <div style={{
                        padding: '15px',
                        borderBottom: '1px solid #00ff00',
                        background: 'rgba(0, 255, 0, 0.05)'
                    }}>
                        <div style={{
                            color: '#00ff00',
                            fontFamily: 'SF Mono, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
                            fontSize: '0.9rem',
                            fontWeight: 'bold',
                            marginBottom: '10px'
                        }}>
                            &gt; SEMANTIC SEARCH
                        </div>
                        <div style={{ display: 'flex', gap: '8px' }}>
                            <input
                                type="text"
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                                placeholder="search documents..."
                                style={{
                                    flex: 1,
                                    background: '#000',
                                    border: '1px solid #00ff00',
                                    color: '#00ff00',
                                    padding: '8px 10px',
                                    fontFamily: 'SF Mono, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
                                    fontSize: '0.8rem',
                                    outline: 'none',
                                    transition: 'box-shadow 0.2s, border-color 0.2s',
                                    boxShadow: hoverGoBtn ? '0 0 8px 1px #00ff00' : 'none',
                                    borderColor: hoverGoBtn ? '#00ff88' : '#00ff00'
                                }}
                                onFocus={e => e.target.style.boxShadow = '0 0 8px 1px #00ff00'}
                                onBlur={e => e.target.style.boxShadow = 'none'}
                            />
                            <button
                                onClick={handleSearch}
                                onMouseEnter={() => setHoverGoBtn(true)}
                                onMouseLeave={() => setHoverGoBtn(false)}
                                style={{
                                    background: hoverGoBtn ? '#00ff00' : '#000',
                                    border: '2px solid #00ff00',
                                    color: hoverGoBtn ? '#000' : '#00ff00',
                                    padding: '8px 16px',
                                    fontFamily: 'SF Mono, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
                                    cursor: 'pointer',
                                    fontSize: '0.8rem',
                                    fontWeight: 'bold',
                                    transition: 'all 0.2s ease',
                                    boxShadow: hoverGoBtn ? '0 0 15px rgba(0, 255, 0, 0.6)' : 'none'
                                }}
                            >
                                GO
                            </button>
                        </div>
                    </div>
                    <div style={{
                        flex: 1,
                        overflowY: 'auto',
                        padding: '15px'
                    }}>
                        {searchResults.length > 0 ? (
                            searchResults.map((result, idx) => (
                                <div 
                                    key={idx} 
                                    onClick={() => handleOpenFile(result.filepath)}
                                    style={{
                                        marginBottom: '12px',
                                        padding: '10px',
                                        border: '1px solid #00ff00',
                                        borderLeft: '3px solid #00ff00',
                                        background: 'rgba(0, 255, 0, 0.05)',
                                        cursor: 'pointer',
                                        transition: 'all 0.2s ease'
                                    }}
                                    onMouseEnter={(e) => {
                                        e.currentTarget.style.background = 'rgba(0, 255, 0, 0.15)';
                                        e.currentTarget.style.borderLeftWidth = '5px';
                                        e.currentTarget.style.boxShadow = '0 0 10px rgba(0, 255, 0, 0.3)';
                                    }}
                                    onMouseLeave={(e) => {
                                        e.currentTarget.style.background = 'rgba(0, 255, 0, 0.05)';
                                        e.currentTarget.style.borderLeftWidth = '3px';
                                        e.currentTarget.style.boxShadow = 'none';
                                    }}
                                >
                                    <div style={{
                                        color: '#00ff00',
                                        fontFamily: 'SF Mono, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
                                        fontSize: '0.85rem',
                                        fontWeight: 'bold',
                                        marginBottom: '5px',
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '5px'
                                    }}>
                                        <span>{result.filename}</span>
                                        <span style={{ fontSize: '0.65rem', opacity: 0.5 }}>▸</span>
                                    </div>
                                    <div style={{
                                        color: '#00ff00',
                                        fontFamily: 'SF Mono, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
                                        fontSize: '0.7rem',
                                        opacity: 0.7,
                                        marginBottom: '5px'
                                    }}>
                                        {result.topic} • {(result.similarity * 100).toFixed(1)}%
                                    </div>
                                    <div style={{
                                        color: '#00ff00',
                                        fontFamily: 'SF Mono, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
                                        fontSize: '0.65rem',
                                        opacity: 0.6,
                                        fontStyle: 'italic'
                                    }}>
                                        {result.preview}
                                    </div>
                                </div>
                            ))
                        ) : (
                            <div style={{
                                color: '#00ff00',
                                fontFamily: 'SF Mono, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
                                fontSize: '0.75rem',
                                opacity: 0.5,
                                textAlign: 'center',
                                marginTop: '40px',
                                letterSpacing: '1px',
                                userSelect: 'none',
                                transition: 'opacity 0.2s'
                            }}>
                                <span style={{filter: 'blur(0.5px)'}}>No search results yet...</span>
                            </div>
                        )}
                    </div>
                </div>

                {/* RAG Section */}
                <div style={{
                    flex: '1',
                    display: 'flex',
                    flexDirection: 'column',
                    overflow: 'hidden'
                }}>
                    <div style={{
                        padding: '15px',
                        borderBottom: '1px solid #00ff00',
                        background: 'rgba(0, 255, 0, 0.05)'
                    }}>
                        <div style={{
                            color: '#00ff00',
                            fontFamily: 'SF Mono, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
                            fontSize: '0.9rem',
                            fontWeight: 'bold',
                            marginBottom: '10px'
                        }}>
                            &gt; ASK RAG
                        </div>
                        <div style={{ display: 'flex', gap: '8px' }}>
                            <input
                                type="text"
                                value={askQuery}
                                onChange={(e) => setAskQuery(e.target.value)}
                                onKeyPress={(e) => e.key === 'Enter' && handleAsk()}
                                placeholder="ask a question..."
                                style={{
                                    flex: 1,
                                    background: '#000',
                                    border: '1px solid #00ff00',
                                    color: '#00ff00',
                                    padding: '8px 10px',
                                    fontFamily: 'SF Mono, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
                                    fontSize: '0.8rem',
                                    outline: 'none',
                                    transition: 'box-shadow 0.2s, border-color 0.2s',
                                    boxShadow: hoverAskBtn ? '0 0 8px 1px #00ff00' : 'none',
                                    borderColor: hoverAskBtn ? '#00ff88' : '#00ff00'
                                }}
                                onFocus={e => e.target.style.boxShadow = '0 0 8px 1px #00ff00'}
                                onBlur={e => e.target.style.boxShadow = 'none'}
                            />
                            <button
                                onClick={handleAsk}
                                disabled={isAsking}
                                onMouseEnter={() => !isAsking && setHoverAskBtn(true)}
                                onMouseLeave={() => setHoverAskBtn(false)}
                                style={{
                                    background: (hoverAskBtn && !isAsking) ? '#00ff00' : '#000',
                                    border: '2px solid #00ff00',
                                    color: isAsking ? '#666' : (hoverAskBtn ? '#000' : '#00ff00'),
                                    padding: '8px 16px',
                                    fontFamily: 'SF Mono, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
                                    cursor: isAsking ? 'wait' : 'pointer',
                                    fontSize: '0.8rem',
                                    fontWeight: 'bold',
                                    transition: 'all 0.2s ease',
                                    boxShadow: (hoverAskBtn && !isAsking) ? '0 0 15px rgba(0, 255, 0, 0.6)' : 'none'
                                }}
                            >
                                {isAsking ? '...' : 'ASK'}
                            </button>
                        </div>
                    </div>
                    <div style={{
                        flex: 1,
                        overflowY: 'auto',
                        padding: '15px'
                    }}>
                        {askAnswer ? (
                            <>
                                <div style={{
                                    marginBottom: '12px',
                                    padding: '10px',
                                    border: '1px solid #00ff00',
                                    background: 'rgba(0, 255, 0, 0.03)'
                                }}>
                                    <div style={{
                                        color: '#00ff00',
                                        fontFamily: 'SF Mono, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
                                        fontSize: '0.7rem',
                                        opacity: 0.7,
                                        marginBottom: '5px'
                                    }}>
                                        Q:
                                    </div>
                                    <div style={{
                                        color: '#00ff00',
                                        fontFamily: 'SF Mono, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
                                        fontSize: '0.8rem'
                                    }}>
                                        {askAnswer.query}
                                    </div>
                                </div>
                                <div style={{
                                    marginBottom: '12px',
                                    padding: '12px',
                                    border: '2px solid #00ff00',
                                    borderLeft: '4px solid #00ff00',
                                    background: 'rgba(0, 255, 0, 0.08)'
                                }}>
                                    <div style={{
                                        color: '#00ff00',
                                        fontFamily: 'SF Mono, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
                                        fontSize: '0.7rem',
                                        opacity: 0.7,
                                        marginBottom: '8px',
                                        fontWeight: 'bold'
                                    }}>
                                        A:
                                    </div>
                                    <div style={{
                                        color: '#00ff00',
                                        fontFamily: 'SF Mono, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
                                        fontSize: '0.8rem',
                                        lineHeight: '1.5',
                                        whiteSpace: 'pre-wrap'
                                    }}>
                                        {askAnswer.answer}
                                    </div>
                                </div>
                                {askAnswer.sources && askAnswer.sources.length > 0 && (
                                    <div>
                                        <div style={{
                                            color: '#00ff00',
                                            fontFamily: 'SF Mono, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
                                            fontSize: '0.75rem',
                                            marginBottom: '8px',
                                            opacity: 0.8
                                        }}>
                                            Sources ({askAnswer.sources.length}):
                                        </div>
                                        {askAnswer.sources.map((source: any, idx: number) => (
                                            <div 
                                                key={idx} 
                                                onClick={() => handleOpenFile(source.filepath)}
                                                style={{
                                                    marginBottom: '8px',
                                                    padding: '8px',
                                                    border: '1px solid #00ff00',
                                                    background: 'rgba(0, 255, 0, 0.02)',
                                                    cursor: 'pointer',
                                                    transition: 'all 0.2s ease'
                                                }}
                                                onMouseEnter={(e) => {
                                                    e.currentTarget.style.background = 'rgba(0, 255, 0, 0.1)';
                                                    e.currentTarget.style.borderColor = '#00ff88';
                                                    e.currentTarget.style.boxShadow = '0 0 10px rgba(0, 255, 0, 0.3)';
                                                }}
                                                onMouseLeave={(e) => {
                                                    e.currentTarget.style.background = 'rgba(0, 255, 0, 0.02)';
                                                    e.currentTarget.style.borderColor = '#00ff00';
                                                    e.currentTarget.style.boxShadow = 'none';
                                                }}
                                            >
                                                <div style={{
                                                    color: '#00ff00',
                                                    fontFamily: 'SF Mono, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
                                                    fontSize: '0.75rem',
                                                    fontWeight: 'bold',
                                                    marginBottom: '3px',
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    gap: '5px'
                                                }}>
                                                    <span>[{idx + 1}]</span>
                                                    <span>{source.filename}</span>
                                                    <span style={{ fontSize: '0.6rem', opacity: 0.5 }}>▸</span>
                                                </div>
                                                <div style={{
                                                    color: '#00ff00',
                                                    fontFamily: 'SF Mono, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
                                                    fontSize: '0.65rem',
                                                    opacity: 0.6
                                                }}>
                                                    {(source.similarity * 100).toFixed(1)}% match
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </>
                        ) : (
                            <div style={{
                                color: '#00ff00',
                                fontFamily: 'SF Mono, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
                                fontSize: '0.75rem',
                                opacity: 0.5,
                                textAlign: 'center',
                                marginTop: '40px',
                                letterSpacing: '1px',
                                userSelect: 'none',
                                transition: 'opacity 0.2s'
                            }}>
                                <span style={{filter: 'blur(0.5px)'}}>Ask a question to get started...</span>
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {message && (
                <div style={{
                    position: 'absolute',
                    top: '50%',
                    left: '50%',
                    transform: 'translate(-50%, -50%)',
                    background: '#000000',
                    padding: '25px 50px',
                    border: '3px solid #00ff00',
                    color: '#00ff00',
                    fontSize: '1.2rem',
                    fontFamily: 'SF Mono, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
                    boxShadow: '0 0 30px rgba(0, 255, 0, 0.7)',
                    textShadow: '0 0 10px #00ff00',
                    zIndex: 1000,
                    fontWeight: 'bold'
                }}>
                    {message}
                </div>
            )}
            
            <style>{`
                @keyframes blink {
                    0%, 49% { opacity: 1; }
                    50%, 100% { opacity: 0; }
                }
            `}</style>
        </div>
    );
};

export default GraphView;

