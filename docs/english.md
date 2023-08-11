---
title: Raqq
description: Early manuscript Kufic
layout: default
language: en-US
direction: ltr
---

_Raqq_ (رَقّ) is a manuscript [Kufic] typeface, intends to revive (as faithfully as possible) the style of Kufic script used in writing the Qur’an in the third century AH. _Raqq_ is Arabic for parchment, on which early Qur’ans were written.

_Raqq_ design is based mostly on the Quran that was endowed to a mosque in Tire in 262 AH by [Amajor al-Turki], then Damascus governor for the Abbasid caliph al-Mu’tamid, and specifically Cambridge University Library manuscript [MS Add.1116].

_Raqq_ Raqq is a free, open source, project, and any one is welcomed to use and modify it under the terms of the version 3 of [GNU Affero General Public License].

_Raqq_ is designed and developed by _Khaled Hosny_, founder of Alif Type.

## Typeface Features
Kufic is one of the oldest forms of Arabic writing, and all early Qur’ans we have access to have been written in some form of it. Kufic has many characteristic features that _Raqq_ tries to capture.

### Spacing
One of the very prominent characteristics of Kufic is the wide spacing between unconnected letters, and the fact that the calligraphic syllable (any sequence of connected letter, that in itself does not connect with proceeds of follows it) is the smallest unit and not the word, and as such spacing between unconnected letter inside the word is the same as the spacing between words, and _Raqq_ replicates this. For example in the _basmala_ here, the space between the _meem_ of the first word and the _alef_ of the second, is the the same between the _alef_ and _lam_ of the second word, despite the first being the spacing between two words and the second is the spacing inside a word:
> بسم الله الرحمن الرحيم
{:.kufi}

In _Raqq_ the spacing can be decreased using the custom font variation axis Spacing (`SPAC`). The _basmala_ at minimum spacing becomes:
> بسم الله الرحمن الرحيم
{:.kufi .s-100}

Similarly, line breaks frequently happen inside the word as long as calligraphic syllables are not broken (in other words, lines can be broken inside a word after _alef_, _dal_, _thal_, _reh_, and _zain_, as they don’t connect to the left, and not after any other letter). Unfortunately, line break opportunities are outside of font control, so if such line breaking is desired, the text should be spelled with spaces between the syllables, for example:
> قُل هوَ ا للهُ أ حد۝١ا للهُ ا لصمد۝٢لَم يلد وَ لم يُو لد۝٣وَ لَم يكن لهُ كفو اً أحد۝٤

> *قُل هوَ ا للهُ أ حد۝١ا*{:.ش٣٧} *للهُ ا لصمد۝٢لَم*{:.ش٤٨} *يلد وَ لـم يُو*{:.ش٥٣} *لد۝٣وَ لَم يكن لهُ*{:.ش٤٦}  *كفو اً أحد*{:.ش٤٣}۝٤
{:.kufi .aligned}

### Elongation
Another prominent Kufic feature is _mashq_, which is elongation of some letters. _Raqq_ provides another custom font variation axis, Mashq (`MSHQ`) for this.

In Kufic, letters that can be elongated are the mostly horizontal ones, namely _dal_, _tah_, _kaf_, _sad_, _beh_, and _feh_. These letters can expand or shrink as needed, though expansion is usually preferred:
> د *د*{:.ش١٠٠} *د*{:.ش٠}<br>
> ط *ط*{:.ش١٠٠} *ط*{:.ش٠}<br>
> ك *ك*{:.ش١٠٠} *ك*{:.ش٠}<br>
> ص *ص*{:.ش١٠٠} *ص*{:.ش٠}<br>
> ٮ *ٮ*{:.ش١٠٠} *ٮ*{:.ش٠}<br>
> ڡ *ڡ*{:.ش١٠٠} *ڡ*{:.ش٠}
{:.kufi}
 
Isolated _ain_ and isolated or final _hah_ can also expand slightly:
> ع *ع*{:.ش١٠٠}<br>
> ح *ح*{:.ش١٠٠}<br>
{:.kufi}

Also final _alef_ can shrink a little:
> ا *ا*{:.ش٠}
{:.kufi}

The rest of the letters do not elongate, but can be elongated by inserting _tatweel_ (_kashida_) after them when needed:
> سائِلون
> سائـِلون
{:.kufi .m100}

### Vowel Dots
Kufic Qur’ans use an early system of [vowel marks], different from the later system in use today. In the old system, _fatha_ is a dot above the letter, _kasra_ is a dot below it, _damma_ is a dot in front (left) of it, and _tanwīn_ is two dots of each. To distinguish these dots from the diacritical dots (like the dots of _beh_ and _teh_), they were written using a different ink than the rest of the text, usually red (but sometimes also green, yellow, and blue, for other reasons).

_Raqq_ utilizes color fonts to automatically represent the color of vowel dots, so regular vowel marks are used and they will appear with the right color in the right positions:
> ◌َ ◌ً ◌ِ ◌ٍ ◌ُ ◌ٌ

> ◌َ ◌ً ◌ِ ◌ٍ ◌ُ ◌ٌ
{:.kufi}

### Diacritical Dots
Kufi Qur’an are often written with or without [diacritical dots] or I‘jam. _Raqq_ supports both. By default the letters are dotted:
> *قل ا عو ذ بر ب ا*{:.ش٢٥} *لفـلق۝١من شر ما خلـق۝٢و من*{:.ش٢٢} *شر غا سق ا ذ ا و قب۝٣*{:.ش١٣} *و من شر ا لنفا ثا ت في ا*{:.ش٢٠} *لعقد۝٤و من شر حا سد*{:.ش٢٧} *ا ذ ا حسد۝٥*{:.ش٤٧}
{:.kufi .aligned}

Using Stylistic Set 1 (`ss01`) feature, the dots can be turned off:
> *قل ا عو ذ بر ب ا*{:.ش٢٥} *لفـلق۝١من شر ما خلـق۝٢و من*{:.ش٢٢} *شر غا سق ا ذ ا و قب۝٣*{:.ش١٣} *و من شر ا لنفا ثا ت في ا*{:.ش٢٠} *لعقد۝٤و من شر حا سد*{:.ش٢٧} *ا ذ ا حسد۝٥*{:.ش٤٧}
{:.kufi .aligned .ss01}

### _Hmaza_
Early Arabic writing didn’t write the _hamza_ (glottal stop) explicit, so in Kufic the same system of vowel dots was used also for the _hamza_, and it was written as red or yellow dot. In _Raqq_ hamza is always a red dot, and its position depends on its vowel:
> أ إ آ ؤ

> أ إ آ ؤ
{:.kufi}

### _Ayah_ Symbol
Colors are used in _ayah_ symbol as well, and there are different symbol for every fifth and tenth _ayah_.

There are many variants of _ayah_ symbol in Kufic Qur’ans, from as simple as three dots or lines in the same text color, to elaborate multi-color variants. _Raqq_ using for regular _ayah_ a three yellow dots in triangular formation with three smaller red dots in between, and it is used when it is not a fifth or tenth _ayah_:
> ۝١

> ۝١
{:.kufi .big}

For fifth _ayah_’s (an _ayah_ symbol followed by a number that ends in five, like 5, 15 and 25, etc.), the _ayah_ symbol looks like a yellow isolated _heh_ (since _heh_ is the number 5 in _abjad_ numbers):
> ۝٥

> ۝٥
{:.kufi .big}

For tenth _ayah_’s (an _ayah_ symbol followed by a number that ends in a zero, like 10, 20 and 30, etc.), the _ayah_ symbol takes a form of decorated circle with the number spelled inside it in yellow ink:
> ۝١٠ ۝٢٠ ۝٣٠

> ۝١٠ ۝٢٠ ۝٣٠
{:.kufi .big}

In some Qur’ans, the fifth _ayah_’s are written like the tenth’s, and _Raqq_ provides an optional variant using Stylistic Alternates (`salt`) feature:
> ۝٥

> ۝٥
{:.kufi .big .salt1}

### Teeth Variation
One of the features of Arabic writing is that when three or more toothed letters (like _beh_ and its family) come next to each other, some of the teeth get raised to differentiate these toothed letters from _seen_ (which has three teeth of its own). This feature probably originated in Kufic or an even earlier form because it was often written dotless, so this variation was very important factor is differentiating these letters. _Raqq_ handles tooth variation automatically:
> تثبتها ؞ سبها ؞ سن ؞ ينتن ؞ متثبتتان

> تثبتها ؞ سبها ؞ سن ؞ ينتن ؞ متثبتتان
{:.kufi .ss01}

### Consecutive Ascenders
One of the stylistic features of _Kufic_ is that when two ascenders come in close proximity, the second of them gets shorter, which also happens automatically in _Raqq_:
> لله ؞ علل ؞ ظل ؞ ظاهر

> لله ؞ علل ؞ ظل ؞ ظاهر
{:.kufi}

### _Hah_
In Kufic, letters preceding _hah_ attach to it from the top, not at baseline, raising them and the letters they connect to above the baseline, and at the same time ascenders don’t exceed the height of the _alef_, so they get shorter as they raise higher and higher. Both happens automatically in _Raqq_:
> الحج ؞ المتلجلج ؞ يضحكون

> الحج ؞ *المتـلجـلج*{:.ش٣٤} ؞ *يضحكون*{:.ش٦٩}
{:.kufi}

### _Yeh_
Isolated and final _yeh_ take several forms in Kufic, some are contextual and some are stylistic.

For example, after a _lam_, _beh_, or _seen_, the final _yeh_ takes a special form, unless there is a diacritic that clashes with this form. _Raqq_ handles this automatically:
> سيء ؞ سِيء ؞ علي ؞ علِي ؞ حتى ؞ حبى

> سيء ؞ سِيء ؞ علي ؞ علِي ؞ حتى ؞ حبى
{:.kufi .s-10}

Some times it takes a form with deeper descender, for stylistic purposes (like filling a void in the line below). This can be activated manually when needed using option 1 of Stylistic Alternates (`salt`) feature:
> ي ؞ لي ؞ في ؞ حي

> ي ؞ لي ؞ في ؞ حي
{:.kufi .salt1}

The font also supports returning _yeh_ (_bari ye_ in Urdu).
It can be activated manually when needed using option 2 of Stylistic Alternates feature:
> أي ؞ على ؞ يا بني ؞ إلي

> أي ؞ على ؞ يا بني ؞ *إلي*{:.ش١٠٠}
{:.kufi .salt2 .s-20}

Or by typing the relevant Unicode character:
> أے ؞ علے ؞ يا بنے ؞ إلے

> أے ؞ علے ؞ يا بنے ؞ *إلے*{:.ش١٠٠}
{:.kufi .s-20}

### _Meem_
Sometimes _meem_ in Kufic connects to specific letters by merely touching them, instead of a full baseline stroke. _Raqq_ will chose the right form of connection from the context:
> من ؞ مما ؞ علما

> من ؞ مما ؞ علما
{:.kufi}

### Letter Relations
Kufic gives a great deal of a attention to the relation between black and white. Spacing between unconnected letters is evenly distributed in the line and the page in general, and so is the spacing between connected letters. But unlike the very wide spacing between unconnected letters, connected letters are very tightly spaced and any empty space is filled except for a minimum hair space that is usually to the space between the two horizontal strokes of the _dal_ and the _sad_.

See how the space between the _feh_ and next letters is meticulously filled:
> ڡا ڡٮ ڡح ڡد ڡه ڡو ڡر ڡط ڡی ڡك ڡل ڡم ڡں ڡس ڡع ڡڡ ڡص ڡق ڡں
{:.kufi .justified}

Similarly, between _hah_ and next letters:
> حا حٮ حح حد حه حو حر حط حی حك حل حم حں حس حع حڡ حص حق حں
{:.kufi .justified}

And so on for the rest of the letters:
> علما ؞ بد ؞ سببا ؞ منها ؞ للسمع
{:.كوفي}

## Feedback
We are happy to see _Raqq_ put in use. We welcome any questions, comments, or suggestions about the typeface or ways to improve it, either by mail on the GitHub project.

> ۝
{:.kufi .big}

[Kufic]: https://en.wikipedia.org/wiki/Kufic
[Amajor al-Turki]: https://en.wikipedia.org/wiki/Amajur_al-Turki
[MS Add.1116]: https://cudl.lib.cam.ac.uk/view/MS-ADD-01116
[GNU Affero General Public License]: https://www.gnu.org/licenses/agpl-3.0.en.html
[vowel marks]: https://en.wikipedia.org/wiki/Arabic_diacritics#Tashkil_(marks_used_as_phonetic_guides)
[diacritical dots]: https://en.wikipedia.org/wiki/Arabic_diacritics#I%E2%80%98j%C4%81m_(phonetic_distinctions_of_consonants)