# Speech Test Word Suite

This suite provides a small, reusable set of words, phrases, and explicit phoneme chains for WaveToy speech-render regression checks. The machine-readable source lives at `test_assets/speech_test_words.json`.

## Categories

- **Basic vowels:** ah, ee, oo, oh, ay, eye, ow, oy
- **Simple CV:** bee, dee, gee, kay, may, no, row, see
- **Plosives:** pop, bob, tap, dad, kick, gag, pipe, ticket
- **Fricatives:** sass, fife, fish, safe, zebra, vision, measure
- **Nasals:** mom, moon, name, mango, sing, ring, morning
- **Liquids:** lily, really, rural, lorry, yellow, railroad
- **Affricates:** church, judge, cheese, jam, chocolate, ginger
- **Difficult combinations:** strength, twelfth, crisps, world, squirrel, sixths
- **Continuous motion:** banana, tomato, potato, elephant, articulation, communication
- **Character voice tests:** hello, good morning, how are you, thank you, welcome aboard
- **Regression phrases:** hello; banana; communication; strength; squirrel; the quick brown fox; pack my box with five dozen liquor jugs; she sells seashells by the seashore

## Explicit phoneme chains

| Label | Chain |
| --- | --- |
| ee-oo oscillation | EE → OO → EE → OO → EE |
| vowel sweep | AH → EE → OO → UW → AY |
| morning | M → AA → N → EE → NG |
| strength stress | S → T → R → EE → NG → TH |
| crash | K → R → AH → SH |

Use these chains as deterministic smoke tests for source assignment, transition rendering, and future continuous-mouth-motion comparisons.
