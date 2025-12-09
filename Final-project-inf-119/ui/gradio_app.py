# Gradio UI for the Verb Conjugator Factory
# Author: [Your Name] - [Student ID]

import gradio as gr
import os
from typing import Tuple
import threading
import time
from mcp import MCPServer, MCPClient, AgentRole
from agents import TrackingAgent, ParserAgent, DesignAgent, CodeGenAgent, TestAgent
from config.api_config import GRADIO_SERVER_NAME, GRADIO_SERVER_PORT, USAGE_REPORT_FILE
from utils.helpers import load_from_file, ensure_directory
import zipfile
import tempfile
from pathlib import Path
import base64

class VerbConjugatorFactoryUI:
    """
    Gradio UI for the multi-agent verb conjugator factory
    """
    
    def __init__(self):
        """Initialize the UI and agents"""
        # Initialize MCP server
        self.mcp_server = MCPServer()
        
        # Initialize agents
        self.tracking_agent = TrackingAgent()
        self.parser_agent = ParserAgent(self.tracking_agent)
        self.design_agent = DesignAgent(self.tracking_agent)
        self.code_gen_agent = CodeGenAgent(self.tracking_agent)
        self.test_agent = TestAgent(self.tracking_agent)
        
        # Ensure output directories exist
        ensure_directory("generated/conjugator")
        ensure_directory("generated/tests")
    
    def generate_application(self, requirements: str):
        """
        Main pipeline to generate the verb conjugator application
        
        Args:
            requirements: User requirements as text
            
        Returns:
            Tuple of (status, generated_code, test_code, usage_report, instructions)
        """
        try:
            # We'll yield progress as tuples matching the outputs plus a progress number
            # Outputs order: status, full_code, test_code, usage_report, instructions, progress

            def _progress_html(p: int) -> str:
                # Use !important to avoid theme overriding styles and make the bar sleek & visible
                return f"""
<div style="width:100%; background:#f0f0f0; border-radius:6px; overflow:hidden; height:10px;">
  <div style="height:100%; width:{p}%; background:linear-gradient(90deg,#27ae60,#2ecc71) !important; border-radius:6px; transition: width 300ms ease; display:block;"></div>
</div>
<div style="font-size:12px; color:#666; margin-top:6px;">Estimated progress: {p}%</div>
"""

            # Step 1: Parse requirements (0-20%)
            yield "📝 Parsing requirements...", "", "", "", "", _progress_html(10)
            spec = self.parser_agent.parse_requirements(requirements)

            # Step 2: Create design (20-40%)
            yield "🎨 Creating design...", "", "", "", "", _progress_html(30)
            design = self.design_agent.create_design(spec)

            # Step 3: Generate code (40-70%) - run generation in background and show incremental progress
            yield "💻 Generating code...", "", "", "", "", _progress_html(50)

            gen_result = {"code": None, "error": None}

            def _run_gen():
                try:
                    gen_result["code"] = self.code_gen_agent.generate_code(spec, design)
                except Exception as e:
                    gen_result["error"] = e

            gen_thread = threading.Thread(target=_run_gen, daemon=True)
            gen_thread.start()

            # While thread is running, increment the visual bar monotonically but keep the
            # displayed percentage label at 50 to avoid a bouncing number.
            visual_width = 50
            max_visual = 69
            while gen_thread.is_alive():
                # slowly increase the visual bar width up to max_visual
                if visual_width < max_visual:
                    visual_width = min(max_visual, visual_width + 1)
                # show the bar loading, but display the percent as 50 until finalization
                yield f"💻 Generating code... (working)", "", "", "", "", _progress_html(visual_width).replace(f'Estimated progress: {visual_width}%', 'Estimated progress: 50%')
                time.sleep(0.4)

            # Thread finished
            if gen_result["error"]:
                raise gen_result["error"]

            generated_code = gen_result["code"]

            # Finalize code stage (bump displayed percent)
            yield "💻 Finalizing code...", "", "", "", "", _progress_html(70)

            # Step 4: Generate tests (70-85%)
            yield "🧪 Generating tests...", "", "", "", "", _progress_html(75)
            test_code = self.test_agent.generate_tests(spec, generated_code)

            # Step 5: Save usage report (85-95%)
            yield "📊 Saving usage report...", "", "", "", "", _progress_html(90)
            self.tracking_agent.save_usage_report()

            # Load generated files
            conjugator_code = load_from_file("generated/conjugator/verb_conjugator.py")
            ui_code = load_from_file("generated/conjugator/gradio_ui.py")

            # Combine code for display
            full_code = f"# verb_conjugator.py\n{conjugator_code}\n\n# gradio_ui.py\n{ui_code}"

            # Load usage report
            usage_report = load_from_file(USAGE_REPORT_FILE)

            # Create instructions
            instructions = self._create_instructions(spec)

            # Done (100%)
            yield "\n\n✅ Generation complete!", full_code, test_code, usage_report, instructions, _progress_html(100)

        except Exception as e:
            error_msg = f"❌ Error: {str(e)}"
            # When an error occurs, yield the error message and set progress to 0
            yield error_msg, "", "", "", "", _progress_html(0)
    
    def _create_instructions(self, spec) -> str:
        """Create instructions for running the generated application"""
        return f"""
# How to Run the Generated Application

## 1. Install Dependencies
```bash
pip install mlconjug3 gradio pytest
```

## 2. Run the Conjugator UI
```bash
cd generated/conjugator
python gradio_ui.py
```

## 3. Run the Tests
```bash
cd generated/tests
pytest test_conjugator.py -v
```

## Application Features
- Supported Languages: {', '.join(spec.languages)}
- Supported Tenses: {', '.join(spec.tenses)}
- Handles Irregular Verbs: {spec.handle_irregular}

## Usage
1. Open the Gradio interface in your browser
2. Enter a verb to conjugate
3. Select language and tense
4. View the conjugation results
"""

    def _make_download_package(self) -> str:
        """Create a zip file containing the generated app, tests, and usage report.

        Returns:
            Path to the created zip file (string)
        """
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
        tmp.close()
        zip_path = tmp.name

        base = Path("generated")
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
            # Add generated directory
            if base.exists():
                for p in base.rglob("*"):
                    z.write(p, p.relative_to(base.parent))

            # Add usage report if present
            usage = Path(USAGE_REPORT_FILE)
            if usage.exists():
                z.write(usage, usage.name)

        return zip_path

    def _make_download_package_autohtml(self) -> str:
        """Create the zip and return an HTML snippet that triggers a browser download via a data URL.

        Returns:
            HTML string that will auto-click a download link for the zip file.
        """
        zip_path = self._make_download_package()
        # Read and base64-encode
        with open(zip_path, "rb") as f:
            b = f.read()
        b64 = base64.b64encode(b).decode("ascii")
        filename = Path(zip_path).name
        html = f'''<div style="font-size:16px; color:#27ae60; margin-bottom:8px;">Your download should start automatically.<br>
If not, <a id="dl" href="data:application/zip;base64,{b64}" download="{filename}">click here</a>.</div>
<script>setTimeout(function(){{document.getElementById('dl').click();}}, 200);</script>'''
        return html
    
    def create_interface(self) -> gr.Blocks:
        """Create the Gradio interface"""
        
        with gr.Blocks(title="Verb Conjugator Factory", theme=gr.themes.Soft()) as interface:
            gr.Markdown("# 🏭 Language Verb Conjugator Factory")
            gr.Markdown("Multi-agent system that generates verb conjugator applications using MCP")



            with gr.Row():
                with gr.Column():
                    requirements_input = gr.Textbox(
                        label="Application Requirements",
                        placeholder="Enter requirements for the verb conjugator...\n\nExample:\nCreate a verb conjugator that supports English and Spanish.\nIt should handle present, past, and future tenses.\nInclude support for irregular verbs.",
                        lines=10
                    )
                    
                    generate_btn = gr.Button("🚀 Generate Application", variant="primary", size="lg")

                with gr.Column():
                    status_output = gr.Textbox(label="Generation Status", lines=10)
                    # Simple HTML/CSS progress bar for a visual indicator (sleek green bar)
                    progress_html = gr.HTML(value="""
<div style="margin-top:8px; width:100%; background:#f0f0f0; border-radius:6px; overflow:hidden; height:10px;">
    <div style="height:10px; width:0%; background:linear-gradient(90deg,#27ae60,#2ecc71); border-radius:6px;"></div>
</div>
""")
            
            with gr.Tabs():
                with gr.Tab("📄 Generated Code"):
                    code_output = gr.Code(label="Application Code", language="python", lines=20)
                
                with gr.Tab("🧪 Test Cases"):
                    test_output = gr.Code(label="Test Code", language="python", lines=20)
                
                with gr.Tab("📊 Usage Report"):
                    usage_output = gr.Code(label="Model Usage Report", language="json", lines=10)
                
                with gr.Tab("📖 Instructions"):
                    instructions_output = gr.Markdown()

            # Connect the button. Our generator yields a sixth output: the HTML progress bar
            generate_btn.click(
                fn=self.generate_application,
                inputs=[requirements_input],
                outputs=[status_output, code_output, test_output, usage_output, instructions_output, progress_html]
            )

            
            # Add examples
            gr.Examples(
                examples=[
                    ["Create a verb conjugator for English and Spanish that supports present, past, and future tenses. Include irregular verb handling."],
                    ["Build a French verb conjugator with present, imperfect, and future tenses. Support both regular and irregular verbs."],
                    ["Make a simple English verb conjugator for present and past tense only."]
                ],
                inputs=[requirements_input]
            )
        
        return interface
    
    def launch(self):
        """Launch the Gradio interface"""
        interface = self.create_interface()
        interface.queue()
        interface.launch(
            server_name=GRADIO_SERVER_NAME,
            server_port=GRADIO_SERVER_PORT,
            share=False
        )
