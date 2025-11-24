import gradio as gr
import nest_asyncio
import yaml
import sys
import logging
from pathlib import Path
from typing import Dict, Any, Tuple
from chromadb import Settings

# Apply nest_asyncio to allow async execution in Gradio
nest_asyncio.apply()

# Setup path to include src
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gradio_app")

# Import project modules
try:
    from src.core.utils.config_loader import _validate_brand_config, list_available_brands, CONFIG_DIR
    from src.core.rag.vector_store import VectorStore
    from src.core.rag.rag_helper import RAGHelper
    from src.core.rag.document_loader import DocumentLoader
    from src.infrastructure.llm.llm_client import LLMClient
    from src.orchestration.microsoft_agent_framework.workflows.content_generation_workflow import (
        build_content_generation_workflow,
    )
    from src.core.prompt.templates import TEMPLATES
except ImportError as e:
    logger.error(f"Failed to import project modules: {e}")
    logger.error(f"Current path: {sys.path}")
    raise

# --- Global State ---
APP_STATE = {}

# --- Initialization ---

def initialize_app():
    """Initialize infrastructure components."""
    logger.info("Initializing application components...")

    # Initialize LLM clients
    # Using 'openrouter' first, fallback to azure if needed
    completion_client = LLMClient()
    completion_client.get_client("openrouter")

    embedding_client = LLMClient()
    embedding_client.get_client("openrouter")

    # Initialize RAG components
    # Persistent ChromaDB
    settings = Settings(anonymized_telemetry=False)
    persist_dir = str(current_dir / "data" / "chroma_db")

    vector_store = VectorStore(persist_directory=persist_dir, settings=settings)
    collection_name = "marketing_content"

    # Ensure collection exists
    collection = vector_store.get_or_create_collection(
        collection_name=collection_name,
        metadata={"hnsw:space": "cosine"}
    )

    document_loader = DocumentLoader()

    global APP_STATE
    APP_STATE.update({
        "vector_store": vector_store,
        "collection": collection,
        "rag_helper": None,  # Initialized after brand config load
        "document_loader": document_loader,
        "completion_client": completion_client,
        "embedding_client": embedding_client,
        "collection_name": collection_name
    })
    logger.info("Application components initialized.")

# --- Brand Management ---

def _initialize_rag_helper(config, brand_name):
    """Helper to initialize RAG for a loaded config."""
    try:
        rag_config = config['models']['vectorization']
        rag_helper = RAGHelper(
            embedding_client=APP_STATE['embedding_client'],
            embedding_model=rag_config.get('model', "openai/text-embedding-3-small"),
            chunk_size=rag_config.get('chunk_size', 150),
            chunk_overlap=rag_config.get('chunk_overlap', 30),
            chunk_threshold=rag_config.get('chunk_threshold', 150)
        )
        APP_STATE['rag_helper'] = rag_helper
        logger.info(f"Initialized RAGHelper for brand: {brand_name}")
        gr.Info(f"Successfully loaded brand: {brand_name}")
        return True, f"Successfully loaded brand: {brand_name}"
    except Exception as e:
        logger.error(f"Failed to initialize RAGHelper: {e}")
        gr.Error(f"Loaded brand {brand_name}, but RAG init failed: {e}")
        return False, f"Loaded brand {brand_name}, but RAG init failed: {e}"

def load_brand_from_disk(brand_name) -> Tuple[Dict[str, Any], str, str]:
    """Load a brand config from the existing configs directory."""
    if not brand_name:
        gr.Warning("Please select a brand.")
        return None, "", "Please select a brand."
    
    try:
        config_path = CONFIG_DIR / f"{brand_name}.yaml"
        if not config_path.exists():
             gr.Error(f"Config not found for {brand_name}")
             return None, "", f"Config not found for {brand_name}"

        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            
        # Validate (re-validate to be safe)
        _validate_brand_config(config, brand_name)
        
        success, msg = _initialize_rag_helper(config, brand_name)
        return config, brand_name, msg
            
    except Exception as e:
        gr.Error(f"Error loading brand {brand_name}: {str(e)}")
        return None, "", f"Error loading brand {brand_name}: {str(e)}"

def process_uploaded_brand(file_obj) -> Tuple[Dict[str, Any], str, str, Any]:
    """Process uploaded brand config: validate, save, and load."""
    if file_obj is None:
        gr.Warning("Please upload a YAML file.")
        return None, "", "Please upload a YAML file.", gr.update()

    try:
        # Read file content
        with open(file_obj.name, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        # Validate structure
        if 'name' not in config:
            gr.Error("Error: YAML must contain a 'name' field.")
            return None, "", "Error: YAML must contain a 'name' field.", gr.update()

        brand_name = config['name']

        # Validate required fields
        try:
            _validate_brand_config(config, brand_name)
        except Exception as e:
            gr.Error(f"Validation Error: {str(e)}")
            return None, "", f"Validation Error: {str(e)}", gr.update()

        # Save to CONFIG_DIR
        target_path = CONFIG_DIR / f"{brand_name}.yaml"
        
        # Save file
        with open(target_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, sort_keys=False)
            
        # Initialize
        success, msg = _initialize_rag_helper(config, brand_name)
        
        # Update available brands list
        new_brands = list_available_brands()
        
        return config, brand_name, f"Saved and loaded brand: {brand_name}", gr.update(choices=new_brands, value=brand_name)

    except Exception as e:
        gr.Error(f"Error processing file: {str(e)}")
        return None, "", f"Error processing file: {str(e)}", gr.update()

def get_brand_document_stats(brand_name):
    """Get document statistics for the brand."""
    if not brand_name:
        return "No brand loaded.", []
    
    collection = APP_STATE.get("collection")
    if not collection:
        return "Vector store not initialized.", []
        
    try:
        # Get all documents for this brand
        result = collection.get(where={"brand": brand_name})
        
        if not result or not result['ids']:
            return "No documents found for this brand.", []
            
        count = len(result['ids'])
        
        # Extract metadata for listing
        docs_list = []
        seen_files = set()
        
        metadatas = result.get('metadatas', [])
        if metadatas:
            for meta in metadatas:
                if meta:
                    filename = meta.get('original_filename', 'Unknown')
                    if filename not in seen_files:
                        # Use list of lists for Dataframe compatibility
                        docs_list.append([
                            filename,
                            meta.get('doc_type', 'Unknown'),
                            meta.get('source', 'Unknown')
                        ])
                        seen_files.add(filename)
        
        return f"Found {count} chunks from {len(docs_list)} unique files.", docs_list
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return f"Error retrieving stats: {str(e)}", []

# --- Document Management ---

def upload_documents(files, brand_name, progress=gr.Progress()):
    """Process uploaded documents for the brand."""
    if not brand_name:
        gr.Warning("Please load a brand configuration first.")
        return "Please load a brand configuration first.", None, "No brand loaded.", []
    if not files:
        gr.Warning("No files uploaded.")
        return "No files uploaded.", None, "No files uploaded.", []

    rag_helper = APP_STATE.get("rag_helper")
    if not rag_helper:
        gr.Error("RAG Helper not initialized. Please reload brand configuration.")
        return "RAG Helper not initialized. Please reload brand configuration.", None, "RAG Helper not initialized.", []

    vector_store = APP_STATE["vector_store"]
    loader = APP_STATE["document_loader"]
    collection_name = APP_STATE["collection_name"]

    total_chunks = 0

    try:
        processed_docs = []
        total_files = len(files)
        
        # Phase 1 & 2: Load, Chunk, and Embed (Iterative)
        for i, file in enumerate(files):
            progress((i / total_files) * 0.9, desc=f"Processing {file.name} ({i+1}/{total_files})...")
            
            # Use the temporary file path provided by Gradio directly
            file_path = Path(file.name)
            
            # Load file
            doc = loader.load_text_file(
                str(file_path),
                metadata={
                    "brand": brand_name, 
                    "doc_type": "uploaded",
                    "original_filename": file_path.name 
                }
            )
            
            # Chunk and Embed immediately for this document
            # This distributes the heavy lifting across the progress bar
            docs = rag_helper.prepare_raw_document(doc)
            processed_docs.extend(docs)

        # Phase 3: Store in Vector DB
        if processed_docs:
            progress(0.9, desc="Storing in vector database...")
            count = vector_store.add_documents(collection_name, processed_docs)
            total_chunks = count

        progress(1.0, desc="Complete!")
        gr.Info(f"Successfully processed {len(files)} files. Added {total_chunks} chunks.")
        
        # Get updated stats
        stats_msg, docs_list = get_brand_document_stats(brand_name)
        
        return f"Successfully processed {len(files)} files. Added {total_chunks} chunks to knowledge base for {brand_name}.", None, stats_msg, docs_list

    except Exception as e:
        logger.exception("Error processing documents")
        gr.Error(f"Error processing documents: {str(e)}")
        return f"Error processing documents: {str(e)}", files, f"Error: {str(e)}", []

def clear_brand_documents(brand_name):
    """Clear documents for the specific brand."""
    if not brand_name:
        gr.Warning("Please load a brand configuration first.")
        return "Please load a brand configuration first.", "No brand loaded.", []

    collection = APP_STATE["collection"]

    try:
        collection.delete(where={"brand": brand_name})
        gr.Info(f"Cleared all documents for brand: {brand_name}")
        return f"Cleared all documents for brand: {brand_name}", "Cleared all documents.", []
    except Exception as e:
        logger.exception("Error clearing documents")
        gr.Error(f"Error clearing documents: {str(e)}")
        return f"Error clearing documents: {str(e)}", f"Error: {str(e)}", []

# --- Content Generation ---


async def generate_content(topic, template_name, examples_list, use_cot, brand_config):
    """Execute the content generation workflow."""
    if not brand_config:
        gr.Warning("Please load a brand configuration first.")
        return "Please load a brand configuration first.", "", "", "", "", None
    if not topic:
        gr.Warning("Please enter a topic.")
        return "Please enter a topic.", "", "", "", "", None

    # Use provided list directly
    examples = examples_list if examples_list else []

    brand_name = brand_config['name']
    quality_threshold = brand_config['models']['content_evaluation'][
        'quality_threshold']

    try:
        # Build workflow
        workflow = build_content_generation_workflow(brand_name)

        # Prepare message
        message = {
            "brand": brand_name,
            "topic": topic,
            "examples": examples,
            "brand_config": brand_config,
            "template": template_name,
            "use_cot": use_cot,
            "max_iterations": 3,
            "quality_threshold": quality_threshold if quality_threshold else 7,
        }

        # Run workflow
        result = await workflow.run(message=message)

        # Extract state
        state = None
        if hasattr(result, "state"):
            state = result.state
        elif hasattr(result, "get_outputs"):
            outs = result.get_outputs()
            if outs:
                # Handle list or single object
                first = outs[0] if isinstance(outs, list) else outs
                if hasattr(first, "state"):
                    state = first.state
                elif isinstance(first, dict) and "state" in first:
                    state = first["state"]

        if not state:
            gr.Error("Error: Could not retrieve workflow state.")
            return "Error: Could not retrieve workflow state.", "", "", "", "", None

        # Format Output
        content = state.content or "No content generated."

        # Iterations
        iterations = f"{state.iteration_count} / {state.max_iterations}"

        # Score
        critique = state.critique
        score_display = "N/A"
        reasoning = "No evaluation available."
        dimension_scores = "N/A"

        if critique:
            score = getattr(critique, "average_score",
                            getattr(critique, "score", 0))
            score_display = f"{score:.2f} / 10.0"
            reasoning = getattr(critique, "reasoning",
                                "No reasoning provided.")
            scores = getattr(critique, "scores", {})
            if scores:
                dimension_scores = "\n".join(
                    [f"- **{k}**: {v:.2f}" for k, v in scores.items()])
        
        # Extract messages for trace
        trace_data = []
        if hasattr(state, "messages"):
            # Convert messages to a JSON-serializable format
            for msg in state.messages:
                # Check if msg is a dict or an object
                if isinstance(msg, dict):
                    trace_data.append({
                        "role": msg.get("role", "unknown"),
                        "content": msg.get("content", ""),
                        "metadata": msg.get("metadata", {})
                    })
                else:
                    trace_data.append({
                        "role": getattr(msg, "role", "unknown"),
                        "content": getattr(msg, "content", ""),
                        "metadata": getattr(msg, "metadata", {})
                    })

        return content, iterations, score_display, dimension_scores, reasoning, trace_data

    except Exception as e:
        logger.exception("Error during generation")
        gr.Error(f"Error generating content: {str(e)}")
        return f"Error generating content: {str(e)}", "", "", "", "", None

    except Exception as e:
        logger.exception("Error during generation")
        return f"Error generating content: {str(e)}", "", "", "", ""

# --- UI Construction ---

def create_ui():
    # Initialize app state
    try:
        if not APP_STATE:
            initialize_app()
    except Exception as e:
        logger.error(f"Initialization failed: {e}")

    with gr.Blocks(title="LevelUp360 Content Generator") as demo:
        # Header with Logo
        with gr.Row(variant="panel", elem_id="header"):
            with gr.Column(scale=1, min_width=150):
                # Path to logo - adjusting to go up one level from examples/marketing_team to examples/assets
                logo_path = str(current_dir.parent / "assets" / "levelup360-inverted-logo-transparent.svg")
                # Read SVG content for direct embedding
                try:
                    with open(logo_path, "r", encoding="utf-8") as f:
                        svg_content = f.read()
                    # Adjust SVG size if needed, or wrap in a div
                    logo_html = f'<div style="height: 80px; width: auto; overflow: hidden;">{svg_content}</div>'
                except Exception as e:
                    logger.error(f"Failed to read logo SVG: {e}")
                    logo_html = f'<div style="color: white; font-weight: bold;">LevelUp360</div>'

                gr.HTML(
                    value=logo_html,
                    show_label=False
                )
            with gr.Column(scale=4):
                gr.Markdown("# LevelUp360 Agentic Content Generator")

        # Get available brands
        available_brands = list_available_brands()
        default_brand = available_brands[0] if len(available_brands) == 1 else None
        
        initial_config = None
        initial_name = ""
        initial_msg = ""
        
        if default_brand:
            # Pre-load if only one brand exists
            try:
                initial_config, initial_name, initial_msg = load_brand_from_disk(default_brand)
            except Exception as e:
                logger.error(f"Failed to auto-load default brand: {e}")

        # State variables
        state_brand_config = gr.State(initial_config)
        state_brand_name = gr.State(initial_name)

        with gr.Tabs():
            # Tab 1: Brand Management
            with gr.Tab("1. Brand Configuration"):
                gr.Markdown("### Select or Upload Brand Configuration")
                
                with gr.Row():
                    with gr.Column(scale=1):
                        brand_dropdown = gr.Dropdown(
                            label="Select Existing Brand", 
                            choices=available_brands,
                            value=default_brand,
                            interactive=True
                        )
                        load_selected_btn = gr.Button("Load Selected Brand", variant="primary", size="sm")
                    
                    with gr.Column(scale=1):
                        brand_name_disp = gr.Textbox(
                            label="Active Brand Name", 
                            value=initial_name, 
                            interactive=False
                        )
                
                gr.Markdown("--- OR ---")
                
                with gr.Row():
                    brand_file = gr.File(label="Upload New Brand Config (YAML)", file_types=[".yaml", ".yml"])
                
                with gr.Column():
                    # Make status message more visible with Markdown headers
                    brand_status = gr.Markdown(f"### {initial_msg}" if initial_msg else "")

                # Callbacks
                load_selected_btn.click(
                    load_brand_from_disk,
                    inputs=[brand_dropdown],
                    outputs=[state_brand_config, state_brand_name, brand_status]
                ).then(
                    lambda name: name,
                    inputs=[state_brand_name],
                    outputs=[brand_name_disp]
                )

                brand_file.upload(
                    process_uploaded_brand,
                    inputs=[brand_file],
                    outputs=[state_brand_config, state_brand_name, brand_status, brand_dropdown]
                ).then(
                    lambda name: name,
                    inputs=[state_brand_name],
                    outputs=[brand_name_disp]
                )

            # Tab 2: Document Management
            with gr.Tab("2. Knowledge Base"):
                gr.Markdown("### Manage Brand Knowledge")
                gr.Markdown("Upload documents (Markdown/Text) to the RAG knowledge base for the loaded brand.")

                with gr.Row():
                    with gr.Column(scale=1):
                        doc_files = gr.File(label="Upload Documents", file_count="multiple", file_types=[".md", ".txt"])
                        with gr.Row():
                            upload_btn = gr.Button("Process & Store", variant="primary", size="sm")
                        doc_status = gr.Markdown("")

                    with gr.Column(scale=1):
                        gr.Markdown("### Current Knowledge Base")
                        stats_display = gr.Markdown("No brand loaded.")
                        refresh_stats_btn = gr.Button("Refresh Stats", size="sm")
                        docs_table = gr.Dataframe(
                            headers=["Filename", "Type", "Source"],
                            datatype=["str", "str", "str"],
                            label="Indexed Documents",
                            interactive=False
                        )
                        clear_btn = gr.Button("Clear/Delete All Stored Documents", variant="stop", size="sm")

                # Callbacks
                upload_btn.click(
                    upload_documents,
                    inputs=[doc_files, state_brand_name],
                    outputs=[doc_status, doc_files, stats_display, docs_table]
                )

                clear_btn.click(
                    clear_brand_documents,
                    inputs=[state_brand_name],
                    outputs=[doc_status, stats_display, docs_table]
                )
                
                refresh_stats_btn.click(
                    get_brand_document_stats,
                    inputs=[state_brand_name],
                    outputs=[stats_display, docs_table]
                )
                
                # Auto-refresh stats when brand changes
                state_brand_name.change(
                    get_brand_document_stats,
                    inputs=[state_brand_name],
                    outputs=[stats_display, docs_table]
                )

            # Tab 3: Content Generation
            with gr.Tab("3. Content Generation"):
                gr.Markdown("### Generate Content")

                with gr.Row():
                    with gr.Column(scale=1):
                        topic_input = gr.Textbox(label="Topic / Prompt", placeholder="Enter topic here...", lines=3)
                        template_dropdown = gr.Dropdown(
                            label="Template",
                            choices=list(TEMPLATES.keys()),
                            value="LINKEDIN_POST_ZERO_SHOT"
                        )
                        
                        # Examples Management (visible only for FEW_SHOT templates)
                        examples_state = gr.State([])
                        
                        # Wrap in a Column for reliable visibility toggling
                        with gr.Column(visible=False) as examples_container:
                            gr.Markdown("### Few-Shot Examples")
                            new_example_input = gr.Textbox(
                                label="Add New Example", 
                                placeholder="Paste example content here...", 
                                lines=3
                            )
                            with gr.Row():
                                add_example_btn = gr.Button("Add Example", size="sm")
                                clear_examples_btn = gr.Button("Clear All Examples", variant="stop", size="sm")
                            
                            examples_display = gr.JSON(label="Current Examples List", value=[])

                        cot_checkbox = gr.Checkbox(label="Use Chain of Thought (CoT)", value=False)
                        generate_btn = gr.Button("Generate Content", variant="primary", size="sm")

                    with gr.Column(scale=2):
                        output_content = gr.Markdown(label="Generated Content")

                        with gr.Accordion("Evaluation & Metadata", open=True):
                            with gr.Row():
                                out_iterations = gr.Textbox(label="Iterations")
                                out_score = gr.Textbox(label="Overall Score")

                            out_dimensions = gr.Markdown(label="Dimension Scores")
                            out_reasoning = gr.Markdown(label="Critique Reasoning")
                        
                        with gr.Accordion("Full System Trace", open=False):
                            trace_json = gr.JSON(label="Workflow Execution Trace")

                # Dynamic visibility for examples
                def on_template_change(template_name):
                    logger.info(f"Template changed to: {template_name}")
                    # Return a dictionary update for the Column component
                    if template_name and "FEW_SHOT" in str(template_name):
                        logger.info("Showing examples container")
                        return gr.update(visible=True)
                    logger.info("Hiding examples container")
                    return gr.update(visible=False)

                template_dropdown.change(
                    on_template_change,
                    inputs=[template_dropdown],
                    outputs=[examples_container]
                )

                # Example management callbacks
                def add_example(new_ex, current_list):
                    if not new_ex or not new_ex.strip():
                        return current_list, current_list, ""
                    updated_list = current_list + [new_ex.strip()]
                    return updated_list, updated_list, ""

                def clear_examples():
                    return [], [], ""

                add_example_btn.click(
                    add_example,
                    inputs=[new_example_input, examples_state],
                    outputs=[examples_state, examples_display, new_example_input]
                )

                clear_examples_btn.click(
                    clear_examples,
                    outputs=[examples_state, examples_display, new_example_input]
                )

                generate_btn.click(
                    generate_content,
                    inputs=[topic_input, template_dropdown, examples_state, cot_checkbox, state_brand_config],
                    outputs=[output_content, out_iterations, out_score, out_dimensions, out_reasoning, trace_json]
                )

    return demo

if __name__ == "__main__":
    ui = create_ui()
    # Remove hardcoded port to allow Gradio to find an available one
    ui.launch(server_name="0.0.0.0")
