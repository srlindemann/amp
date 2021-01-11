import pandas as pd

import vendors2.kibot.metadata.load.kibot_metadata as kmd


class MockKibotMetadata(kmd.KibotMetadata):
    @classmethod
    def read_tickbidask_contract_metadata(cls) -> pd.DataFrame:
        return pd.DataFrame.from_dict({'SymbolBase': ['ES', 'ES', 'ES', 'ES', 'ES', 'ES', 'ES', 'ES', 'ES', 'ES', 'ES', 'ES', 'ES', 'ES', 'ES', 'ES', 'ES', 'ES', 'ES', 'ES', 'ES', 'ES', 'ES', 'ES', 'ES'], 'Symbol': ['ES', 'ESH11', 'ESH12', 'ESH13', 'ESH14', 'ESH15', 'ESH16', 'ESH17', 'ESH18', 'ESH19', 'ESH20', 'ESM10', 'ESM11', 'ESM12', 'ESM13', 'ESM14', 'ESM15', 'ESM16', 'ESM17', 'ESM18', 'ESM19', 'ESM20', 'ESU10', 'ESU11', 'ESU12'], 'StartDate': [pd.Timestamp('2009-09-30 00:00:00'), pd.Timestamp('2010-04-06 00:00:00'), pd.Timestamp('2011-03-06 00:00:00'), pd.Timestamp('2012-03-19 00:00:00'), pd.Timestamp('2013-03-06 00:00:00'), pd.Timestamp('2014-01-06 00:00:00'), pd.Timestamp('2015-01-06 00:00:00'), pd.Timestamp('2016-02-02 00:00:00'), pd.Timestamp('2017-01-06 00:00:00'), pd.Timestamp('2018-01-16 00:00:00'), pd.Timestamp('2019-01-11 00:00:00'), pd.Timestamp('2010-06-07 00:00:00'), pd.Timestamp('2010-05-04 00:00:00'), pd.Timestamp('2011-03-21 00:00:00'), pd.Timestamp('2012-04-23 00:00:00'), pd.Timestamp('2013-03-27 00:00:00'), pd.Timestamp('2014-05-21 00:00:00'), pd.Timestamp('2015-04-12 00:00:00'), pd.Timestamp('2016-04-13 00:00:00'), pd.Timestamp('2017-06-16 00:00:00'), pd.Timestamp('2018-06-11 00:00:00'), pd.Timestamp('2019-03-25 00:00:00'), pd.Timestamp('2010-04-01 00:00:00'), pd.Timestamp('2010-08-09 00:00:00'), pd.Timestamp('2011-06-17 00:00:00')], 'Size(MB)': [50610.0, 891.0, 1060.0, 848.0, 1075.0, 1351.0, 2158.0, 968.0, 1550.0, 1925.0, 0.03, 133.0, 1054.0, 1229.0, 1313.0, 1073.0, 1103.0, 1446.0, 1060.0, 1744.0, 1999.0, 0.01, 76.0, 1686.0, 1216.0], 'Description': ['CONTINUOUS E-MINI S&P 500 CONTRACT', 'E-MINI S&P 500 MARCH 2011', 'E-MINI S&P 500 MARCH 2012', 'E-MINI S&P 500 MARCH 2013', 'E-MINI S&P 500 MARCH 2014', 'E-MINI S&P 500 MARCH 2015', 'E-MINI S&P 500 MARCH 2016', 'E-MINI S&P 500 MARCH 2017', 'E-MINI S&P 500 MARCH 2018', 'E-MINI S&P 500 MARCH 2019', 'E-MINI S&P 500 MARCH 2020', 'E-MINI S&P 500 JUNE 2010', 'E-MINI S&P 500 JUNE 2011', 'E-MINI S&P 500 JUNE 2012', 'E-MINI S&P 500 JUNE 2013', 'E-MINI S&P 500 JUNE 2014', 'E-MINI S&P 500 JUNE 2015', 'E-MINI S&P 500 JUNE 2016', 'E-MINI S&P 500 JUNE 2017', 'E-MINI S&P 500 JUNE 2018', 'E-MINI S&P 500 JUNE 2019', 'E-MINI S&P 500 JUNE 2020', 'E-MINI S&P 500 SEPTEMBER 2010', 'E-MINI S&P 500 SEPTEMBER 2011', 'E-MINI S&P 500 SEPTEMBER 2012'], 'Exchange': ['Chicago Mercantile Exchange Mini Sized Contracts (CME MINI)', 'Chicago Mercantile Exchange Mini Sized Contracts (CME MINI)', 'Chicago Mercantile Exchange Mini Sized Contracts (CME MINI)', 'Chicago Mercantile Exchange Mini Sized Contracts (CME MINI)', 'Chicago Mercantile Exchange Mini Sized Contracts (CME MINI)', 'Chicago Mercantile Exchange Mini Sized Contracts (CME MINI)', 'Chicago Mercantile Exchange Mini Sized Contracts (CME MINI)', 'Chicago Mercantile Exchange Mini Sized Contracts (CME MINI)', 'Chicago Mercantile Exchange Mini Sized Contracts (CME MINI)', 'Chicago Mercantile Exchange Mini Sized Contracts (CME MINI)', 'Chicago Mercantile Exchange Mini Sized Contracts (CME MINI)', 'Chicago Mercantile Exchange Mini Sized Contracts (CME MINI)', 'Chicago Mercantile Exchange Mini Sized Contracts (CME MINI)', 'Chicago Mercantile Exchange Mini Sized Contracts (CME MINI)', 'Chicago Mercantile Exchange Mini Sized Contracts (CME MINI)', 'Chicago Mercantile Exchange Mini Sized Contracts (CME MINI)', 'Chicago Mercantile Exchange Mini Sized Contracts (CME MINI)', 'Chicago Mercantile Exchange Mini Sized Contracts (CME MINI)', 'Chicago Mercantile Exchange Mini Sized Contracts (CME MINI)', 'Chicago Mercantile Exchange Mini Sized Contracts (CME MINI)', 'Chicago Mercantile Exchange Mini Sized Contracts (CME MINI)', 'Chicago Mercantile Exchange Mini Sized Contracts (CME MINI)', 'Chicago Mercantile Exchange Mini Sized Contracts (CME MINI)', 'Chicago Mercantile Exchange Mini Sized Contracts (CME MINI)', 'Chicago Mercantile Exchange Mini Sized Contracts (CME MINI)']})

    @classmethod
    def read_continuous_contract_metadata(cls) -> pd.DataFrame:
        return pd.DataFrame.from_dict({'SymbolBase': ['JY', 'TY', 'FV', 'ES', 'EU', 'GC', 'US', 'AD', 'NQ', 'CL', 'BP', 'CD', 'SI', 'HG', 'YM', 'SF', 'UB', 'TU', 'RTY', 'NG', 'NE', 'M6E', 'NIY', 'QM', 'PX'], 'Symbol': ['JY', 'TY', 'FV', 'ES', 'EU', 'GC', 'US', 'AD', 'NQ', 'CL', 'BP', 'CD', 'SI', 'HG', 'YM', 'SF', 'UB', 'TU', 'RTY', 'NG', 'NE', 'M6E', 'NIY', 'QM', 'PX'], 'StartDate': [pd.Timestamp('2009-09-27 00:00:00'), pd.Timestamp('2009-09-27 00:00:00'), pd.Timestamp('2009-09-27 00:00:00'), pd.Timestamp('2009-09-27 00:00:00'), pd.Timestamp('2009-09-27 00:00:00'), pd.Timestamp('2009-09-27 00:00:00'), pd.Timestamp('2009-09-27 00:00:00'), pd.Timestamp('2009-09-27 00:00:00'), pd.Timestamp('2009-09-27 00:00:00'), pd.Timestamp('2009-09-27 00:00:00'), pd.Timestamp('2009-09-27 00:00:00'), pd.Timestamp('2009-09-27 00:00:00'), pd.Timestamp('2009-09-27 00:00:00'), pd.Timestamp('2009-09-27 00:00:00'), pd.Timestamp('2009-09-27 00:00:00'), pd.Timestamp('2009-09-27 00:00:00'), pd.Timestamp('2010-01-10 00:00:00'), pd.Timestamp('2009-09-27 00:00:00'), pd.Timestamp('2009-09-27 00:00:00'), pd.Timestamp('2009-09-27 00:00:00'), pd.Timestamp('2009-09-27 00:00:00'), pd.Timestamp('2009-09-27 00:00:00'), pd.Timestamp('2009-09-28 00:00:00'), pd.Timestamp('2009-09-27 00:00:00'), pd.Timestamp('2009-09-27 00:00:00')], 'Size(MB)': [183.0, 180.0, 171.0, 162.0, 160.0, 156.0, 154.0, 152.0, 150.0, 146.0, 145.0, 142.0, 137.0, 137.0, 133.0, 123.0, 115.0, 115.0, 114.0, 109.0, 104.0, 104.0, 99.0, 97.0, 96.0], 'Description': ['CONTINUOUS JAPANESE YEN CONTRACT', 'CONTINUOUS 10 YR US TREASURY NOTE CONTRACT', 'CONTINUOUS 5 YR US TREASURY NOTE CONTRACT', 'CONTINUOUS E-MINI S&P 500 CONTRACT', 'CONTINUOUS EURO FX CONTRACT', 'CONTINUOUS GOLD CONTRACT', 'CONTINUOUS 30 YR US TREASURY BOND CONTRACT', 'CONTINUOUS AUSTRALIAN DOLLAR CONTRACT', 'CONTINUOUS E-MINI NASDAQ 100 CONTRACT', 'CONTINUOUS CRUDE OIL CONTRACT', 'CONTINUOUS BRITISH POUND CONTRACT', 'CONTINUOUS CANADIAN DOLLAR CONTRACT', 'CONTINUOUS SILVER CONTRACT', 'CONTINUOUS COPPER CONTRACT', 'CONTINUOUS E-MINI DOW JONES $5 CONTRACT', 'CONTINUOUS SWISS FRANC CONTRACT', 'CONTINUOUS ULTRA US TREASURY BOND CONTRACT', 'CONTINUOUS 2 YR US TREASURY NOTE CONTRACT', 'CONTINUOUS E-MINI RUSSELL 2000 CONTRACT', 'CONTINUOUS NATURAL GAS CONTRACT', 'CONTINUOUS NEW ZEALAND DOLLAR CONTRACT', 'CONTINUOUS E-MICRO EUR/USD CONTRACT', 'CONTINUOUS NIKKEI 225 YEN INDEX CONTRACT', 'CONTINUOUS E-MINI CRUDE OIL CONTRACT', 'CONTINUOUS MEXICAN PESO CONTRACT'], 'Exchange': ['Chicago Mercantile Exchange (CME GLOBEX)', 'Chicago Board Of Trade (CBOT GLOBEX)', 'Chicago Board Of Trade (CBOT GLOBEX)', 'Chicago Mercantile Exchange Mini Sized Contracts (CME MINI)', 'Chicago Mercantile Exchange (CME GLOBEX)', 'Commodities Exchange Center (COMEX GLOBEX)', 'Chicago Board Of Trade (CBOT GLOBEX)', 'Chicago Mercantile Exchange (CME GLOBEX)', 'Chicago Mercantile Exchange Mini Sized Contracts (CME MINI)', 'New York Mercantile Exchange (NYMEX GLOBEX)', 'Chicago Mercantile Exchange (CME GLOBEX)', 'Chicago Mercantile Exchange (CME GLOBEX)', 'Commodities Exchange Center (COMEX GLOBEX)', 'Commodities Exchange Center (COMEX GLOBEX)', 'Chicago Board Of Trade Mini Sized Contracts (CBOT MINI)', 'Chicago Mercantile Exchange (CME GLOBEX)', 'Chicago Board Of Trade (CBOT GLOBEX)', 'Chicago Board Of Trade (CBOT GLOBEX)', 'Chicago Mercantile Exchange Mini Sized Contracts (CME MINI)', 'New York Mercantile Exchange (NYMEX GLOBEX)', 'Chicago Mercantile Exchange (CME GLOBEX)', 'Chicago Mercantile Exchange (CME GLOBEX)', 'Chicago Mercantile Exchange (CME GLOBEX)', 'New York Mercantile Exchange Mini Sized Contracts', 'Chicago Mercantile Exchange (CME GLOBEX)']})

    @classmethod
    def read_1min_contract_metadata(cls) -> pd.DataFrame:
        return pd.DataFrame.from_dict({'Symbol': ['JY', 'JYF18', 'JYF19', 'JYG18', 'JYG19', 'JYH10', 'JYH11', 'JYH12', 'JYH13', 'JYH14', 'JYH15', 'JYH16', 'JYH17', 'JYH18', 'JYH19', 'JYH20', 'JYJ17', 'JYJ18', 'JYJ19', 'JYK17', 'JYK18', 'JYK19', 'JYM10', 'JYM11', 'JYM12'], 'Link': ['http://api.kibot.com/?action=download&link=15171e1f1l1cim1k1f1r1e1l1bzmm41ezm1a19im181t1e1t1b191rm41t1c1512161t1r1e1912immpm41rzm1j141l1pimikivm41f1c1e191b1g151pimmjm41r1e151b1e12151e19immjmhmjmhmjmtmpmpm4121f1b19171eimmjm4151e1e15171k1j191c1eimmjm41b191d1t1p151b1r191r1r1f1l1cimmpm41t1r191bim1514191ciz171l1j17151r1em61c191em41a151r1r1v1l1b12im191819mc191b191d1aaiam7v7f', 'http://api.kibot.com/?action=download&link=vrv1vcv9vdvpnmvav9vlvcvdvk4mmhvc4mvbvsnmv2vivcvivkvsvlmhvivpvrvev6vivlvcvsvenmmjmhvl4mvtvhvdvjnmnanunemtmcmhv9vpvcvsvkv5vrvjnmmtmhvlvcvrvkvcvevrvcvsnmmtm3mtm3mtmimjmjmhvev9vkvsv1vcnmmtmhvrvcvcvrv1vavtvsvpvcnmmtmhvkvsv7vivjvrvkvlvsvlvlv9vdvpnmmjmhvivlvsvknmvrvhvsvpn4v1vdvtv1vrvlvcm6vpvsvcmhvbvrvlvlvuvdvkvenmvsv2vsmpvsvkvsv7vbaiama87n7d7n7v', 'http://api.kibot.com/?action=download&link=8r8185898d8pnm8a898l858d8k4mmv854m8b8inm828685868k8i8lmv868p8r8e8j868l858i8enmmgmv8l4m8c8v8d8gnmnansnemcm6mv898p858i8k8t8r8gnmmcmv8l858r8k858e8r858inmmcm3mcm3mcm6mgmgmv8e898k8i8185nmmcmv8r85858r818a8c8i8p85nmmcmv8k8i8u868g8r8k8l8i8l8l898d8pnmmgmv868l8i8knm8r8v8i8pn4818d8c818r8l85mj8p8i85mv8b8r8l8l8s8d8k8enm8i828imp8i8k8i8u8baiama87n7u7n7v', 'http://api.kibot.com/?action=download&link=vrv1vcvkv4vsnmv7vkvevcv4vfpmmhvcpmvbvznmv2vivcvivfvzvemhvivsvrvdv6vivevcvzvdnmmjmhvepmvtvhv4vjnmn7nunzmtmcmhvkvsvcvzvfv5vrvjnmmtmhvevcvrvfvcvdvrvcvznmmtm3mtm3mtmimjmjmhvdvkvfvzv1vcnmmtmhvrvcvcvrv1v7vtvzvsvcnmmtmhvfvzvavivjvrvfvevzvevevkv4vsnmmjmhvivevzvfnmvrvhvzvsnpv1v4vtv1vrvevcm6vsvzvcmhvbvrvevevuv4vfvdnmvzv2vzmsvzvfvzvavbaiamap7n7d7n7v', 'http://api.kibot.com/?action=download&link=8r81858k848inm8u8k8e85848fpmmv85pm8b8znm828685868f8z8emv868i8r8d8j868e858z8dnmmgmv8epm8c8v848gnmnunsnzmcm6mv8k8i858z8f8t8r8gnmmcmv8e858r8f858d8r858znmmcm3mcm3mcm6mgmgmv8d8k8f8z8185nmmcmv8r85858r818u8c8z8i85nmmcmv8f8z8a868g8r8f8e8z8e8e8k848inmmgmv868e8z8fnm8r8v8z8inp81848c818r8e85mj8i8z85mv8b8r8e8e8s848f8dnm8z828zmi8z8f8z8a8baiamap7n7u7n7v', 'http://api.kibot.com/?action=download&link=vrv1v5v9vdv4nkvmv9vlv5vdvbpkk8v5pkvavsnkvzvtv5vtvbvsvlk8vtv4vrv2vjvtvlv5vsv2nkkik8vlpkvcv8vdvinknmn6nzkckik8v9v4v5vsvbvuvrvinkkck8vlv5vrvbv5v2vrv5vsnkkck3kck3kcktkikik8v2v9vbvsv1v5nkkck8vrv5v5vrv1vmvcvsv4v5nkkck8vbvsv7vtvivrvbvlvsvlvlv9vdv4nkkik8vtvlvsvbnkvrv8vsv4npv1vdvcv1vrvlv5kjv4vsv5k8vavrvlvlv6vdvbv2nkvsvzvsk4vsvbvsv7vaaiamal7n7v7n7v', 'http://api.kibot.com/?action=download&link=iri1i5i9idi4nkimi9ili5idibpkkti5pkiaiunkizivi5ivibiuilktivi4iri2i6ivili5iui2nkk8ktilpkihitidi8nknmngnzkhkhkti9i4i5iuibiciri8nkkhktili5iribi5i2iri5iunkkhk3khk3khkvk8k8kti2i9ibiui1i5nkkhktiri5i5iri1imihiui4i5nkkhktibiui7ivi8iribiliuilili9idi4nkk8ktiviliuibnkiritiui4npi1idihi1irili5k6i4iui5ktiairililigidibi2nkiuiziuk4iuibiui7iaaiamal7n7n7n7v', 'http://api.kibot.com/?action=download&link=vrv1v5v9vdvmnkvbv9vlv5vdvipkkev5pkvavsnkvuvtv5vtvivsvlkevtvmvrvzvjvtvlv5vsvznkk2kevlpkvcvevdv2nknbn6nukckmkev9vmv5vsviv4vrv2nkkckevlv5vrviv5vzvrv5vsnkkck3kck3kcktk2k2kevzv9vivsv1v5nkkckevrv5v5vrv1vbvcvsvmv5nkkckevivsv7vtv2vrvivlvsvlvlv9vdvmnkk2kevtvlvsvinkvrvevsvmnpv1vdvcv1vrvlv5kjvmvsv5kevavrvlvlv6vdvivznkvsvuvskmvsvivsv7vaaiamal7n727n7v', 'http://api.kibot.com/?action=download&link=vivuv5v9vfv41kvmv9v8v5vfvbpkklv5pkvavs1kvzvtv5vtvbvsv8klvtv4viv2vjvtv8v5vsv21kknklv8pkvcvlvfvn1k1m161zkckfklv9v4v5vsvbvdvivn1kkcklv8v5vivbv5v2viv5vs1kkck3kck3kcktknknklv2v9vbvsvuv51kkcklviv5v5vivuvmvcvsv4v51kkcklvbvsv7vtvnvivbv8vsv8v8v9vfv41kknklvtv8vsvb1kvivlvsv41pvuvfvcvuviv8v5kjv4vsv5klvaviv8v8v6vfvbv21kvsvzvsk4vsvbvsv7vaaiamal7n757n7v', 'http://api.kibot.com/?action=download&link=vrv1v5v9vdv8nev2v9vlv5vdvbpee4v5pevkvsnevzvtv5vtvbvsvle4vtv8vrvuvjvtvlv5vsvuneeme4vlpevcv4vdvmnen2n6nzeceke4v9v8v5vsvbvavrvmneece4vlv5vrvbv5vuvrv5vsneece3ece3ecetememe4vuv9vbvsv1v5neece4vrv5v5vrv1v2vcvsv8v5neece4vbvsv7vtvmvrvbvlvsvlvlv9vdv8neeme4vtvlvsvbnevrv4vsv8npv1vdvcv1vrvlv5ejv8vsv5e4vkvrvlvlv6vdvbvunevsvzvse8vsvbvsv7vkaiamal7n7f7n7v', 'http://api.kibot.com/?action=download&link=v3viv5v9vdv48kvmv9v1v5vdvbpkknv5pkvavs8kvzvtv5vtvbvsv1knvtv4v3v2vjvtv1v5vsv28kkrknv1pkvcvnvdvr8k8m868zkcklknv9v4v5vsvbvfv3vr8kkcknv1v5v3vbv5v2v3v5vs8kkckukckukcktkrkrknv2v9vbvsviv58kkcknv3v5v5v3vivmvcvsv4v58kkcknvbvsv7vtvrv3vbv1vsv1v1v9vdv48kkrknvtv1vsvb8kv3vnvsv48pvivdvcviv3v1v5kjv4vsv5knvav3v1v1v6vdvbv28kvsvzvsk4vsvbvsv7vaaiamal7n7e7n7v', 'http://api.kibot.com/?action=download&link=vrv1v5v9vdvunivmv9vlv5vdvz8iipv58iv4vsnivkvtv5vtvzvsvlipvtvuvrv2vjvtvlv5vsv2niiaipvl8ivcvpvdvaninmn6nkicizipv9vuv5vsvzvbvrvaniicipvlv5vrvzv5v2vrv5vsniici3ici3icitiaiaipv2v9vzvsv1v5niicipvrv5v5vrv1vmvcvsvuv5niicipvzvsv7vtvavrvzvlvsvlvlv9vdvuniiaipvtvlvsvznivrvpvsvun8v1vdvcv1vrvlv5ijvuvsv5ipv4vrvlvlv6vdvzv2nivsvkvsiuvsvzvsv7v4aiamal7n7c7n7v', 'http://api.kibot.com/?action=download&link=v8v5vuv9vdv43kvmv9vnvuvdvbpkkrvupkvavs3kvzvtvuvtvbvsvnkrvtv4v8v2vjvtvnvuvsv23kk1krvnpkvcvrvdv13k3m363zkcknkrv9v4vuvsvbvlv8v13kkckrvnvuv8vbvuv2v8vuvs3kkckikckikcktk1k1krv2v9vbvsv5vu3kkckrv8vuvuv8v5vmvcvsv4vu3kkckrvbvsv7vtv1v8vbvnvsvnvnv9vdv43kk1krvtvnvsvb3kv8vrvsv43pv5vdvcv5v8vnvukjv4vsvukrvav8vnvnv6vdvbv23kvsvzvsk4vsvbvsv7vaaiamal7n7r7n7v', 'http://api.kibot.com/?action=download&link=vrv1vcv9vdv4nkvmv9vlvcvdvbpkkhvcpkvavsnkvzvivcvivbvsvlkhviv4vrv2v6vivlvcvsv2nkkjkhvlpkvtvhvdvjnknmnunzktkckhv9v4vcvsvbv5vrvjnkktkhvlvcvrvbvcv2vrvcvsnkktk3ktk3ktkikjkjkhv2v9vbvsv1vcnkktkhvrvcvcvrv1vmvtvsv4vcnkktkhvbvsv7vivjvrvbvlvsvlvlv9vdv4nkkjkhvivlvsvbnkvrvhvsv4npv1vdvtv1vrvlvck6v4vsvckhvavrvlvlvuvdvbv2nkvsvzvsk4vsvbvsv7vaaiamal7n7d7n7v', 'http://api.kibot.com/?action=download&link=8r8185898d84nk8m898l858d8bpkkv85pk8a8ink8z8685868b8i8lkv86848r828j868l858i82nkkgkv8lpk8c8v8d8gnknmnsnzkck6kv8984858i8b8t8r8gnkkckv8l858r8b85828r858inkkck3kck3kck6kgkgkv82898b8i8185nkkckv8r85858r818m8c8i8485nkkckv8b8i8u868g8r8b8l8i8l8l898d84nkkgkv868l8i8bnk8r8v8i84np818d8c818r8l85kj848i85kv8a8r8l8l8s8d8b82nk8i8z8ik48i8b8i8u8aaiamal7n7u7n7v', 'http://api.kibot.com/?action=download&link=jrj1j4j9jdjmnkjbj9jlj4jdjgpkk8j4pkjajvnkjsjcj4jcjgjvjlk8jcjmjrjzj2jcjlj4jvjznkkik8jlpkj5j8jdjinknbnhnskmkik8j9jmj4jvjgjujrjinkk5k8jlj4jrjgj4jzjrj4jvnkk5k3k5k3k5kckikik8jzj9jgjvj1j4nkk5k8jrj4j4jrj1jbj5jvjmj4nkk5k8jgjvj7jcjijrjgjljvjljlj9jdjmnkkik8jcjljvjgnkjrj8jvjmnpj1jdj5j1jrjlj4k2jmjvj4k8jajrjljljhjdjgjznkjvjsjvkmjvjgjvj7jaaiamal727v7n7v', 'http://api.kibot.com/?action=download&link=v8v5vuv9vdv43mvav9vnvuvdvpkmmrvukmvbvs3mv2vtvuvtvpvsvnmrvtv4v8vzvjvtvnvuvsvz3mm1mrvnkmvcvrvdv13m3a363amcmnmrv9v4vuvsvpvlv8v13mmcmrvnvuv8vpvuvzv8vuvs3mmcmimcmimcmtm1m1mrvzv9vpvsv5vu3mmcmrv8vuvuv8v5vavcvsv4vu3mmcmrvpvsv7vtv1v8vpvnvsvnvnv9vdv43mm1mrvtvnvsvp3mv8vrvsv43kv5vdvcv5v8vnvumjv4vsvumrvbv8vnvnv6vdvpvz3mvsv2vsm4vsvpvsv7vbaiamai7n7r7n7v', 'http://api.kibot.com/?action=download&link=vrv1vcv9vdv4nmvav9vlvcvdvpkmmhvckmvbvsnmv2vivcvivpvsvlmhviv4vrvzv6vivlvcvsvznmmjmhvlkmvtvhvdvjnmnanunamtmcmhv9v4vcvsvpv5vrvjnmmtmhvlvcvrvpvcvzvrvcvsnmmtm3mtm3mtmimjmjmhvzv9vpvsv1vcnmmtmhvrvcvcvrv1vavtvsv4vcnmmtmhvpvsv7vivjvrvpvlvsvlvlv9vdv4nmmjmhvivlvsvpnmvrvhvsv4nkv1vdvtv1vrvlvcm6v4vsvcmhvbvrvlvlvuvdvpvznmvsv2vsm4vsvpvsv7vbaiamai7n7d7n7v', 'http://api.kibot.com/?action=download&link=8r8185898d84nm8a898l858d8pkmmv85km8b8inm828685868p8i8lmv86848r8z8j868l858i8znmmgmv8lkm8c8v8d8gnmnansnamcm6mv8984858i8p8t8r8gnmmcmv8l858r8p858z8r858inmmcm3mcm3mcm6mgmgmv8z898p8i8185nmmcmv8r85858r818a8c8i8485nmmcmv8p8i8u868g8r8p8l8i8l8l898d84nmmgmv868l8i8pnm8r8v8i84nk818d8c818r8l85mj848i85mv8b8r8l8l8s8d8p8znm8i828im48i8p8i8u8baiamai7n7u7n7v', 'http://api.kibot.com/?action=download&link=v8v5vuvdvevl3mvnvdvavuvev9fmmkvufmvbvs3mv2vtvuvtv9vsvamkvtvlv8vrvjvtvavuvsvr3mm1mkvafmvcvkvev13m3n363dmcmamkvdvlvuvsv9vpv8v13mmcmkvavuv8v9vuvrv8vuvs3mmcmimcmimcmtm1m1mkvrvdv9vsv5vu3mmcmkv8vuvuv8v5vnvcvsvlvu3mmcmkv9vsv7vtv1v8v9vavsvavavdvevl3mm1mkvtvavsv93mv8vkvsvl3fv5vevcv5v8vavumjvlvsvumkvbv8vavav6vev9vr3mvsv2vsmlvsv9vsv7vbaiamaj7n7r7n7v', 'http://api.kibot.com/?action=download&link=vkv1vcvdvevlamvnvdvpvcvev9fmmhvcfmvbvsamv2vivcviv9vsvpmhvivlvkvrv6vivpvcvsvrammjmhvpfmvtvhvevjamanauadmtmcmhvdvlvcvsv9v5vkvjammtmhvpvcvkv9vcvrvkvcvsammtm3mtm3mtmimjmjmhvrvdv9vsv1vcammtmhvkvcvcvkv1vnvtvsvlvcammtmhv9vsv7vivjvkv9vpvsvpvpvdvevlammjmhvivpvsv9amvkvhvsvlafv1vevtv1vkvpvcm6vlvsvcmhvbvkvpvpvuvev9vramvsv2vsmlvsv9vsv7vbaiamaj7n7d7n7v', 'http://api.kibot.com/?action=download&link=8k81858d8e8lam8n8d8p858e89fmmv85fm8b8iam82868586898i8pmv868l8k8r8j868p858i8rammgmv8pfm8c8v8e8gamanasadmcm6mv8d8l858i898t8k8gammcmv8p858k89858r8k858iammcm3mcm3mcm6mgmgmv8r8d898i8185ammcmv8k85858k818n8c8i8l85ammcmv898i8u868g8k898p8i8p8p8d8e8lammgmv868p8i89am8k8v8i8laf818e8c818k8p85mj8l8i85mv8b8k8p8p8s8e898ram8i828iml8i898i8u8baiamaj7n7u7n7v', 'http://api.kibot.com/?action=download&link=vrv1vev9vdvhnmvjv9vlvevdv3cmm8vecmvbvsnmv2vkvevkv3vsvlm8vkvhvrvtvavkvlvevsvtnmmim8vlcmvzv8vdvinmnjn6n5mzmim8v9vhvevsv3vuvrvinmmzm8vlvevrv3vevtvrvevsnmmzm5mzm5mzmkmimim8vtv9v3vsv1venmmzm8vrvevevrv1vjvzvsvhvenmmzm8v3vsv7vkvivrv3vlvsvlvlv9vdvhnmmim8vkvlvsv3nmvrv8vsvhncv1vdvzv1vrvlvemavhvsvem8vbvrvlvlv6vdv3vtnmvsv2vsmhvsv3vsv7vbaiamag7n7v7n7v', 'http://api.kibot.com/?action=download&link=iri1iei9idihnmiji9ilieidi3cmmkiecmibiunmi2ivieivi3iuilmkivihiriti6ivilieiuitnmm8mkilcmipikidi8nmnjngn5mpmpmki9ihieiui3iziri8nmmpmkilieiri3ieitirieiunmmpm5mpm5mpmvm8m8mkiti9i3iui1ienmmpmkirieieiri1ijipiuihienmmpmki3iui7ivi8iri3iliuilili9idihnmm8mkiviliui3nmirikiuihnci1idipi1iriliem6ihiuiemkibirililigidi3itnmiui2iumhiui3iui7ibaiamag7n7n7n7v', 'http://api.kibot.com/?action=download&link=vrv1viv9vdvjnmvev9vlvivdv3cmm4vicmvbvsnmv2vkvivkv3vsvlm4vkvjvrvzvavkvlvivsvznmmtm4vlcmvuv4vdvtnmnen6n5mumjm4v9vjvivsv3vhvrvtnmmum4vlvivrv3vivzvrvivsnmmum5mum5mumkmtmtm4vzv9v3vsv1vinmmum4vrvivivrv1vevuvsvjvinmmum4v3vsv7vkvtvrv3vlvsvlvlv9vdvjnmmtm4vkvlvsv3nmvrv4vsvjncv1vdvuv1vrvlvimavjvsvim4vbvrvlvlv6vdv3vznmvsv2vsmjvsv3vsv7vbaiamag7n727n7v'], 'Description': ['CONTINUOUS JAPANESE YEN CONTRACT', 'JAPANESE YEN JANUARY 2018', 'JAPANESE YEN JANUARY 2019', 'JAPANESE YEN FEBRUARY 2018', 'JAPANESE YEN FEBRUARY 2019', 'JAPANESE YEN MARCH 2010', 'JAPANESE YEN MARCH 2011', 'JAPANESE YEN MARCH 2012', 'JAPANESE YEN MARCH 2013', 'JAPANESE YEN MARCH 2014', 'JAPANESE YEN MARCH 2015', 'JAPANESE YEN MARCH 2016', 'JAPANESE YEN MARCH 2017', 'JAPANESE YEN MARCH 2018', 'JAPANESE YEN MARCH 2019', 'JAPANESE YEN MARCH 2020', 'JAPANESE YEN APRIL 2017', 'JAPANESE YEN APRIL 2018', 'JAPANESE YEN APRIL 2019', 'JAPANESE YEN MAY 2017', 'JAPANESE YEN MAY 2018', 'JAPANESE YEN MAY 2019', 'JAPANESE YEN JUNE 2010', 'JAPANESE YEN JUNE 2011', 'JAPANESE YEN JUNE 2012']})

    @classmethod
    def read_kibot_exchange_mapping(cls) -> pd.DataFrame:
        return pd.DataFrame.from_dict({'Exchange_group': ['CME', 'CME', 'CME', 'CME', 'CME', 'CME', 'CME', 'CME', 'CME', 'CME', 'CME', 'ICE', 'ICE', 'ICE', 'CME', 'CME', 'ICE', 'CME', 'CME', 'CME', 'CME', 'CME', 'CME', 'CME', 'ICE'], 'Exchange_abbreviation': ['CBOT', 'CBOT', 'CME', 'CBOT', 'NYMEX', 'CBOT', 'CBOT', 'NYMEX', 'CBOT', 'NYMEX', 'CBOT', 'ICE', 'ICE', 'ICE', 'CME', 'NYMEX', 'ICE', 'COMEX', 'COMEX', 'CME', 'CME', 'COMEX', 'COMEX', 'CME', 'ICE'], 'Exchange_symbol': ['EH', 'AW', 'LE', 'ZL', 'BZT', 'ZC', 'ZC', 'CJ', 'ZC', 'CL', 'ZC', 'T', 'CT', 'CT', 'DC', 'BB', 'ATW', 'GC', 'GCK', 'GF', 'HE', 'HG', 'HGT', 'HO', 'O']})
