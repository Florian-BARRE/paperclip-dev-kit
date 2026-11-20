# Configurer `.ppdk/project.toml`

## `[project]`

| Clé | Défaut | Rôle |
|---|---|---|
| `base` | `"main"` | La branche dans laquelle le travail est mergé. Les étapes push et ci comparent la branche à `origin/<base>` (ou `<base>` sans remote). |
| `timeout` | `900` | Secondes accordées par défaut à une règle longue (`ppdk.command`). |

## Les étapes

Chaque table `[[on.<étape>]]` lance une règle, dans l'ordre du fichier.

| Étape | Déclenchée par | Fichiers vus par les règles | Version lue |
|---|---|---|---|
| `commit` | le hook git `pre-commit` | les fichiers indexés (ajoutés, modifiés, renommés) | celle de l'index : ce qui est vraiment commité, pas l'arbre de travail |
| `push` | le hook git `pre-push` | les fichiers changés depuis la base de merge avec `origin/<base>` | `HEAD` |
| `ci` | `ppdk check ci` dans un workflow | comme `push` | `HEAD` |

Sans aucune table `[[on.ci]]`, l'étape ci reprend les règles de `[[on.push]]`.

## Les clés d'une règle

| Clé | Défaut | Rôle |
|---|---|---|
| `rule` | obligatoire | `ppdk.<nom>` pour une règle du kit, `rules.<fichier>` pour `.ppdk/rules/<fichier>.py` |
| `severity` | `"error"` | `"error"` refuse le commit ou le push ; `"warn"` signale sans bloquer |
| `paths` | tous les fichiers | Motifs glob. La règle ne tourne que si un fichier changé correspond, et ne voit que ceux-là. `*` traverse aussi les dossiers : `src/**` et `src/*` veulent dire « sous src/ ». |
| toute autre clé | | Une option de la règle. Une option inconnue de la règle est refusée. |

Une même règle peut apparaître plusieurs fois, avec des options ou des `paths` différents.

## Les règles du kit

| Règle | Étapes utiles | Ce qu'elle refuse | Options |
|---|---|---|---|
| `ppdk.base_branch` | commit, push | un commit sur la branche de base, un push qui la met à jour ; passe toujours en ci | — |
| `ppdk.env_file` | commit | un fichier `.env` ou `.env.*` | `allow` : noms autorisés (défaut `[".env.example"]`) |
| `ppdk.secret` | commit | une ligne au format d'un secret connu : clé privée, clés AWS, GitHub, Anthropic, OpenAI, Slack | `patterns` : expressions régulières en plus |
| `ppdk.conflict_marker` | commit | une ligne `<<<<<<<` ou `>>>>>>>` (pas `=======`, souligné de titre en Markdown) | — |
| `ppdk.file_size` | commit | un fichier au-delà de la limite | `max_kb` (défaut 1024) |
| `ppdk.command` | push, ci | une commande du dépôt qui sort en erreur ou dépasse son délai | `command` (liste, obligatoire), `timeout` (secondes) |

Les fichiers binaires et supprimés sont ignorés par les règles qui lisent le contenu.

## Le rapport

```
ppdk commit: 3 rule(s)
  ok     ppdk.base_branch
  FAIL   ppdk.secret
         conf.py:4: looks like a secret (AWS access key): remove it, ...
  skip   rules.structure_check (no matching file)
ppdk commit: refused, 1 rule(s) blocking. Fix every finding above, then run the commit again.
```

| Statut | Sens | Bloque |
|---|---|---|
| `ok` | la règle n'a rien trouvé | non |
| `FAIL` | constats sur une règle `error` | oui |
| `warn` | constats sur une règle `warn` | non |
| `skip` | la règle a des `paths` et aucun fichier changé ne correspond | non |
| `BROKEN` | la règle est introuvable, mal configurée, ou a levé une exception | oui : la règle doit être corrigée |

Codes de sortie : `0` passé, `1` refusé, `2` le kit n'a pas pu tourner (pas de dépôt, configuration invalide).
`ppdk -v …` ou `PPDK_VERBOSE=1` affiche les journaux du kit.
