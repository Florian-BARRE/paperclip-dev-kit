# Écrire une règle de dépôt

Une règle de dépôt vérifie ce que les règles du kit ne savent pas : la structure du code, les règles
des coding standards propres au projet, une convention de nommage, l'absence d'import interdit…

## Le contrat

- **Un fichier par règle** dans `.ppdk/rules/`, nommé en `snake_case` : c'est ce nom qu'on écrit dans
  `project.toml` (`rule = "rules.structure_check"`).
- **Une seule sous-classe concrète de `ppdk.Rule`** définie dans le fichier. Les classes importées ne
  comptent pas ; deux classes concrètes, ou aucune, rendent la règle `BROKEN`.
- **`run(self, context)` est obligatoire** et renvoie un `RuleResult` : `RuleResult.ok()`, ou
  `RuleResult(findings=(...))` / `RuleResult.fail(Finding(...), ...)`.
- Un `Finding` dit **ce qui ne va pas et comment corriger**, avec le fichier et la ligne quand c'est
  possible : c'est ce que l'agent lira pour corriger.

```python
# ====== Code Summary ======
# Refuses imports from a layer the module may not depend on.

# ====== Standard Library Imports ======
from __future__ import annotations

import re
from typing import ClassVar

# ====== Third-Party Library Imports ======
from ppdk import Finding, Rule, RuleContext, RuleResult


class LayerImportRule(Rule):
    """Refuses `from app.routes` imports outside the routes layer.

    Options:
        forbidden (str): The module prefix that may not be imported.
    """

    OPTIONS: ClassVar[frozenset[str]] = frozenset({"forbidden"})

    _pattern: re.Pattern[str]

    def _configure(self) -> None:
        """Read the options once: a bad value fails before anything runs."""
        forbidden = self._option("forbidden", str, "app.routes")
        self._pattern = re.compile(rf"^\s*(from|import)\s+{re.escape(forbidden)}\b")

    def run(self, context: RuleContext) -> RuleResult:
        """Check every changed Python file outside the routes layer."""
        findings = []
        for path in context.changed_files:
            text = context.read_text(path)
            if text is None or not path.endswith(".py") or "/routes/" in path:
                continue
            for number, line in enumerate(text.splitlines(), start=1):
                if self._pattern.match(line):
                    findings.append(Finding("routes are imported only by the app", path, number))
        return RuleResult(findings=tuple(findings))
```

```toml
[[on.commit]]
rule = "rules.layer_import"
paths = ["src/**"]
forbidden = "app.routes"
```

## Ce que le contexte donne

| Attribut | Contenu |
|---|---|
| `context.stage` | `Stage.COMMIT`, `Stage.PUSH` ou `Stage.CI` |
| `context.changed_files` | les fichiers ajoutés ou modifiés, déjà réduits aux `paths` de la règle |
| `context.read_text(path)` | le texte du fichier **dans la version vérifiée** (l'index au commit, `HEAD` ensuite) ; `None` s'il est binaire ou supprimé |
| `context.reader.read_bytes(path)` | le contenu brut |
| `context.repo_root` | le chemin du dépôt, pour lire un fichier non modifié ou lancer un outil |
| `context.branch`, `context.base_branch` | la branche courante (`None` en CI détachée) et la branche de base |
| `context.default_timeout` | le délai par défaut du projet |

Lire avec `context.read_text` plutôt que d'ouvrir le fichier : au commit, l'arbre de travail peut
différer de ce qui est réellement commité.

## Options

- Déclarer les noms acceptés dans `OPTIONS` : toute autre clé est refusée au chargement.
- Les lire et les valider dans `_configure` avec `self._option(nom, type, défaut)` ou
  `self._string_list_option(nom, défaut)` ; sans défaut, l'option est obligatoire.
- Une valeur invalide : lever `ppdk.RuleConfigError` avec un message précis.

## Erreurs

Le kit isole chaque règle : une règle qui lève une exception est affichée `BROKEN` avec l'exception et
la ligne, les autres règles tournent quand même, et le commit est refusé tant que la règle n'est pas
corrigée. `ppdk validate` charge toutes les règles sans les exécuter : à lancer après chaque
modification de `.ppdk/`.

## Partager du code entre règles

Un module d'aide dont le nom commence par `_` (`.ppdk/rules/_layers.py`) s'importe depuis une règle avec
`from rules._layers import LAYERS`. Il ne doit pas définir de sous-classe concrète de `Rule`.
