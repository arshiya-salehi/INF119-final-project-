# Code Generation Agent - Generates the conjugator application code
# Author: [Your Name] - [Student ID]

from typing import Optional, List
from mcp import MCPClient, AgentRole, RequirementSpec, DesignSpec, GeneratedCode
from agents.tracking_agent import TrackingAgent
from utils.helpers import clean_code_block, save_to_file
from config.api_config import CONJUGATOR_DIR

class CodeGenAgent:
    """
    Agent responsible for generating the verb conjugator application code
    """
    
    def __init__(self, tracking_agent: TrackingAgent, mcp_client: Optional[MCPClient] = None):
        """Initialize code generation agent"""
        self.tracking_agent = tracking_agent
        self.mcp_client = mcp_client
    
    def generate_code(self, spec: RequirementSpec, design: DesignSpec) -> List[GeneratedCode]:
        """
        Generate application code based on requirements and design
        
        Args:
            spec: Requirement specification
            design: Design specification
            
        Returns:
            List of GeneratedCode objects
        """
        if self.mcp_client:
            self.mcp_client.notify({"event": "code_generation_started"})
        
        generated_files = []
        
        # Generate main conjugator module
        conjugator_code = self._generate_conjugator(spec, design)
        generated_files.append(conjugator_code)
        
        # Generate Gradio UI
        ui_code = self._generate_ui(spec)
        generated_files.append(ui_code)
        
        # Save generated files
        for gen_code in generated_files:
            filepath = f"{CONJUGATOR_DIR}/{gen_code.filename}"
            save_to_file(gen_code.code, filepath)
        
        if self.mcp_client:
            self.mcp_client.notify({
                "event": "code_generation_completed",
                "files": [gc.filename for gc in generated_files]
            })
        
        return generated_files
    def _generate_conjugator(self, spec: RequirementSpec, design: DesignSpec) -> GeneratedCode:
        """Generate the main conjugator module"""
        prompt = """You are writing the ONLY implementation of verb_conjugator.py.

Your output must be valid Python that defines:

    class ConjugationError(Exception)
    class VerbConjugator
    def conjugate_verb(language, verb, tense)

This implementation MUST target the REAL mlconjug3 version 3.11.0 conjugation API.

Correct usage:

    import mlconjug3
    conj = mlconjug3.Conjugator(language="<lang>")
    verb_obj = conj.conjugate(verb)
    info = verb_obj.conjug_info

The structure ALWAYS looks like:

    info = {
        "<MoodName>": {
            "<TenseName>": {
                "<pronoun>": "<form>",
                ...
            },
            ...
        },
        ...
    }

There is NO "moods" key and NO "tenses" key in this version.  
You MUST use the structure exactly as returned.

SUPPORTED LANGUAGES:
    English → "en"
    French  → "fr"
    Spanish → "es"

Language normalization rules:
    "English", "english", "en", "EN" → "en"
    "French",  "french",  "fr", "FR" → "fr"
    "Spanish", "spanish", "es", "ES" → "es"

Anything else MUST raise:
    ConjugationError("Unsupported language: " + language)

SUPPORTED TENSES:
    "present"
    "past"
    "future"

Tense normalization rules:
    tense must be string  
    tense.strip().lower() must be one of {"present","past","future"}

Otherwise raise:
    ConjugationError("Unsupported tense: " + tense)


TENSE MAPPINGS

### ENGLISH (en)

    Mood: "indicative"

    present → ("indicative", ["indicative present"])
    past    → ("indicative", ["indicative past tense"])
    future  → ("indicative", ["indicative future"])

English pronoun mapping:

    "I"         ← "I"
    "You"       ← "you"
    "He/She/It" ← "he/she/it"
    "We"        ← "we"
    "They"      ← "they"

Required pronouns (in this exact order):
    ["I", "You", "He/She/It", "We", "They"]


### FRENCH (fr)

mlconjug3 v3.11.0 shows French moods and tenses exactly as:

    Mood: "Indicatif"
    Tenses: "Présent", "Imparfait", "Futur", "Passé Simple"

French tense mappings:

    present → ("Indicatif", ["Présent", "present", "présent"])
    past    → ("Indicatif", ["Passé Simple", "passé simple", "PASSE SIMPLE"])
    future  → ("Indicatif", ["Futur", "futur"])

French pronoun mapping:

    "Je"        ← "je"
    "Tu"        ← "tu"
    "Il/Elle"   ← "il/elle"
    "Nous"      ← "nous"
    "Ils/Elles" ← "ils/elles"

Required pronouns:
    ["Je", "Tu", "Il/Elle", "Nous", "Ils/Elles"]


### SPANISH (es)

mlconjug3 returns Spanish present tense as:

    OrderedDict([
        ('yo', 'corro'),
        ('tú', 'corres'),
        ('él', 'corre'),
        ('nosotros', 'corremos'),
        ('vosotros', 'corréis'),
        ('ellos', 'corren')
    ])

Spanish tense mappings:

    present → ("Indicativo", ["Indicativo Presente", "Indicativo presente"])
    past    → ("Indicativo", [
                    "Indicativo pretérito perfecto simple",
                    "Indicativo Pretérito perfecto simple"
               ])
    future  → ("Indicativo", ["Indicativo Futuro", "Indicativo futuro"])

Spanish pronoun mapping (must match REAL keys):

    "Yo"         ← "yo"
    "Tú"         ← "tú"
    "Él/Ella"    ← "él"
    "Nosotros"   ← "nosotros"
    "Ellos/Ellas"← "ellos"

Ignore "vosotros" unless you want an optional sixth form.

Required pronouns:
    ["Yo", "Tú", "Él/Ella", "Nosotros", "Ellos/Ellas"]


ERROR RULES

Your code MUST check that all required pronoun keys are present and nonempty.

If ANY required pronoun is missing or empty, raise EXACTLY:

    ConjugationError(
        "Could not find conjugations for: " + str(missing_list) +
        " for verb '" + verb + "' in '" + tense + "' tense for " + language + "."
    )


SPECIAL REQUIRED BEHAVIOR

If language is English or "en", tense is present, and verb == "nonexistentverb",
raise EXACTLY:

    ConjugationError("Verb 'nonexistentverb' not found or unsupported for English in present tense.")


CONJUGATION PROCESS

1. Validate inputs.
2. Normalize language.
3. Normalize tense.
4. Create the conjugator:

       conj = mlconjug3.Conjugator(language=<normalized>)

5. Call verb_obj = conj.conjugate(verb).
6. Extract info = verb_obj.conjug_info.
7. Look up the correct mood.
8. Try each candidate tense until one matches.
9. Retrieve its pronoun→form dictionary.
10. For each required pronoun:
        - look up the mapped mlconjug key
        - ensure it exists and is not empty
11. Build the output dict.
12. Return it.

Return ONLY the Python source code for verb_conjugator.py, nothing else.

"""

        code = self.tracking_agent.generate_content(prompt)
        code = clean_code_block(code)

        return GeneratedCode(
            filename="verb_conjugator.py",
            code=code,
            description="Main verb conjugator module",
            dependencies=["mlconjug3"]
        )


    def _generate_ui(self, spec: RequirementSpec) -> GeneratedCode:
        """Generate Gradio UI code"""

        prompt = f"""
Generate a complete Gradio UI in a file named gradio_ui.py for the verb conjugator.

The UI must:

1. Import the public API like this:
   from verb_conjugator import conjugate_verb, ConjugationError

2. Use gr.Blocks to build the interface.

3. Provide:
   - A textbox for the verb (single line, with a helpful placeholder).
   - A dropdown for language with these display choices:
       {', '.join(spec.languages)}
   - A dropdown for tense with these choices:
       {', '.join(spec.tenses)}

4. When the user clicks a button labeled "Conjugate":
   - Read the verb, language, and tense from the inputs.
   - Pass them to conjugate_verb(language, verb, tense).
     The language should be passed exactly as selected from the dropdown.
     The tense can be normalized to lower case before the call.
   - If conjugate_verb returns a dict of pronouns to forms, format it nicely as
     multiple lines of "Pronoun: form".
   - If conjugate_verb raises ConjugationError, catch it and display the error
     message text in a clear way instead of crashing.

5. Layout:
   - Have a title such as "Verb Conjugator".
   - Brief instructions under the title.
   - Inputs and button grouped together.
   - An output area (Textbox or Markdown) to show the result.

6. Launching:
   - Wrap the interface in a function or variable named demo.
   - Protect the launch with:
         if __name__ == "__main__":
             demo.launch()
   - Do not launch automatically on import.

Other constraints:

- Use only top level imports: "import gradio as gr" and
  "from verb_conjugator import conjugate_verb, ConjugationError".
- Do not include any placeholder code or comments that conflict with the API above.

Return ONLY the Python code for gradio_ui.py, nothing else.
"""

        code = self.tracking_agent.generate_content(prompt)
        code = clean_code_block(code)

        return GeneratedCode(
            filename="gradio_ui.py",
            code=code,
            description="Gradio user interface",
            dependencies=["gradio", "verb_conjugator"]
        )
