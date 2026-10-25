"""Reviewed, pinned STEP inputs; no translation alignment or restricted lexicon."""
COMMIT='be4191f0082aeedddb0eff0c02c966292b2bd641'
SOURCE_URL='https://github.com/STEPBible/STEPBible-Data'
LICENSE_URL='https://creativecommons.org/licenses/by/4.0/'
FILES={
 'greek-lexicon':('Lexicons/TBESG - Translators Brief lexicon of Extended Strongs for Greek - STEPBible.org CC BY.txt','312f723d7b8ef263bbdfb0451c9b8057125804dfff390b6f8544cff2a84b57f4',4736912),
 'greek-gospels':('Translators Amalgamated OT+NT/TAGNT Mat-Jhn - Translators Amalgamated Greek NT - STEPBible.org CC-BY.txt','ab8eaaeb68e17a1dcfa34e1e9350358f22f03bc2a97244d848750ad81044bc8e',14189032),
 'greek-rest':('Translators Amalgamated OT+NT/TAGNT Act-Rev - Translators Amalgamated Greek NT - STEPBible.org CC-BY.txt','524e32375361e6d3fa2f7ef00b87605fdc4317a762f395651a05fdc31ad031b7',15939932),
 'hebrew-torah':('Translators Amalgamated OT+NT/TAHOT Gen-Deu - Translators Amalgamated Hebrew OT - STEPBible.org CC BY.txt','e9b8546ee48fe0bfc57c3b70f5f40e98d96580e803526d19026224e31753368b',18190455),
 'hebrew-history':('Translators Amalgamated OT+NT/TAHOT Jos-Est - Translators Amalgamated Hebrew OT - STEPBible.org CC BY.txt','195fee1dc3653bab33701f170734eb894ed647c10cd08cc61749375fe8b73775',24500317),
 'hebrew-writings':('Translators Amalgamated OT+NT/TAHOT Job-Sng - Translators Amalgamated Hebrew OT - STEPBible.org CC BY.txt','bb508af3af07822fca84cc43a0eba79eb70eecf672aabc0245b8d8cecf329d96',9540623),
 'hebrew-prophets':('Translators Amalgamated OT+NT/TAHOT Isa-Mal - Translators Amalgamated Hebrew OT - STEPBible.org CC BY.txt','f3ded203d2a74d6368932c97ae550d1d0754b271af491dc0dedf36fe3ba0bcc5',17977518),
}
DOWNLOAD_BYTES=sum(size for _,_,size in FILES.values())
CORPORA={
 'tagnt-na27':'TAGNT · NA27 membership · supplied source spellings',
 'tahot-main':'TAHOT · L/Q main reading · supplied segmentation',
}
NOTICE=('STEPBible / Tyndale House, Cambridge · CC BY 4.0. '+SOURCE_URL+' @ '+COMMIT+'. '
        'Transformed into a local lexical/token index. TAGNT: only records explicitly listing NA27; '
        'supplied spellings, not a reconstructed critical text. TAHOT: main L/Q records, '
        'including Qere, excluding R/X additions and other alternatives. Reference addresses '
        'follow the supplied NRSV convention; original alternate references and token identities retained. '
        'Hebrew brief glosses/lemma forms come from TAHOT, not TBESH definitions. '
        'TBESH definitions and TTESV translation alignment are excluded. '
        'English lexical content is not a French translation or an assertion of passage-specific meaning.')

STEP_BOOKS=('Gen Exo Lev Num Deu Jos Jdg Rut 1Sa 2Sa 1Ki 2Ki 1Ch 2Ch Ezr Neh Est Job Psa Pro Ecc Sng '
            'Isa Jer Lam Ezk Dan Hos Jol Amo Oba Jon Mic Nam Hab Zep Hag Zec Mal '
            'Mat Mrk Luk Jhn Act Rom 1Co 2Co Gal Eph Php Col 1Th 2Th 1Ti 2Ti Tit Phm Heb Jas 1Pe 2Pe 1Jn 2Jn 3Jn Jud Rev').split()
OSIS_BOOKS=('Gen Exod Lev Num Deut Josh Judg Ruth 1Sam 2Sam 1Kgs 2Kgs 1Chr 2Chr Ezra Neh Esth Job Ps Prov Eccl Song '
            'Isa Jer Lam Ezek Dan Hos Joel Amos Obad Jonah Mic Nah Hab Zeph Hag Zech Mal '
            'Matt Mark Luke John Acts Rom 1Cor 2Cor Gal Eph Phil Col 1Thess 2Thess 1Tim 2Tim Titus Phlm Heb Jas 1Pet 2Pet 1John 2John 3John Jude Rev').split()
BOOKS=dict(zip(STEP_BOOKS,OSIS_BOOKS))
