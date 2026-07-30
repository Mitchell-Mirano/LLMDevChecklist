from .rules.structure import FileExistenceRule, SectionHierarchyRule
from .rules.consistency import RegexConstraintRule, ItemCountConsistencyRule
from .rules.advanced import (
    NoHardcodedTablesRule,
    CiteVerificationRule,
    OrphanLabelRule,
    EquationEnvironmentRule,
    LiteraturePDFNamingRule
)

def get_unmsm_rules():
    """Returns the set of rules defined by MANUSCRIPT-TESIS.md"""
    return [
        FileExistenceRule([
            "tesis.tex",
            "bibliografia.bib",
            "chapters/01_problema_investigacion.tex",
            "chapters/02_revision_literatura.tex",
            "chapters/03_hipotesis_variables.tex",
            "chapters/04_materiales_metodos.tex",
            "chapters/05_resultados.tex",
            "chapters/06_conclusiones.tex",
            "chapters/07_anexos.tex"
        ]),
        
        SectionHierarchyRule(
            "chapters/01_problema_investigacion.tex",
            [
                "Descripción del problema (situación problemática)",
                "Definición del problema",
                "Objetivos",
                "Justificación e importancia de la investigación",
                "Hallazgos y limitaciones de la investigación"
            ]
        ),
        
        SectionHierarchyRule(
            "chapters/04_materiales_metodos.tex",
            [
                "Área de estudio",
                "Diseño de investigación",
                "Población y muestra",
                "Procedimientos, técnicas e instrumentos de recolección de datos",
                "Análisis de datos / análisis estadístico"
            ]
        ),
        
        SectionHierarchyRule(
            "chapters/05_resultados.tex",
            ["Presentación y análisis de los resultados"],
            allow_additional=False # Chapter 5 should only have one main section, rest should be subsections
        ),
        
        RegexConstraintRule(
            "bibliografia.bib",
            r"^\s*note\s*=",
            required=False,
            error_message="Found 'note' field in bibliography. Please use 'annote' to hide internal notes from the final PDF."
        ),
        
        ItemCountConsistencyRule([
            {"file": "chapters/01_problema_investigacion.tex", "pattern": r"\\item", "name": "Problemas"},
            {"file": "chapters/01_problema_investigacion.tex", "pattern": r"\\item", "name": "Objetivos"},
        ]),
        
        NoHardcodedTablesRule("chapters/05_resultados.tex"),
        NoHardcodedTablesRule("chapters/04_materiales_metodos.tex"),
        
        CiteVerificationRule(
            tex_files=[
                "chapters/01_problema_investigacion.tex",
                "chapters/02_revision_literatura.tex",
                "chapters/03_hipotesis_variables.tex",
                "chapters/04_materiales_metodos.tex",
                "chapters/05_resultados.tex",
                "chapters/06_conclusiones.tex",
            ],
            bib_file="bibliografia.bib"
        ),
        
        OrphanLabelRule(
            tex_files=[
                "chapters/01_problema_investigacion.tex",
                "chapters/02_revision_literatura.tex",
                "chapters/03_hipotesis_variables.tex",
                "chapters/04_materiales_metodos.tex",
                "chapters/05_resultados.tex",
                "chapters/06_conclusiones.tex",
            ]
        ),
        
        EquationEnvironmentRule(
            tex_files=[
                "chapters/01_problema_investigacion.tex",
                "chapters/02_revision_literatura.tex",
                "chapters/03_hipotesis_variables.tex",
                "chapters/04_materiales_metodos.tex",
                "chapters/05_resultados.tex",
            ]
        ),
        
        LiteraturePDFNamingRule(
            lit_folder="../1_literature/papers",
            bib_file="bibliografia.bib"
        )
    ]
