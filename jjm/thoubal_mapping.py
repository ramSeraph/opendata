import csv
from pathlib import Path

keys = ['S. No.','State','JJM District','JJM Block','JJM PanchayatId','JJM Panchayat','JJM VillageId','JJM Village','LGD VillageId','LGD Village']
correction_txt = """
237660	Charangpat	591638	Charangpat Maklang	269941
237660	Charangpat	591639	Charangpat Mamang	269968
237660	Charangpat	591640	Nepra Company	269940
279674	Heirok I	591641	Heirok Part I	269981
237662	Heirok Pt Ii	591643	Heirok Part Ii	914323
237661	Heirok Pt Iii	591642	Chingdompok	914327
237693	Irong Chessaba	591713	Irong Chesaba	269919
237664	Kangyambem	591651	Kangthokchao	269978
237664	Kangyambem	591665	Kangyambem	269979
237663	Khangabok I	591644	Hayel Labuk	269939
237663	Khangabok I	631611	Khangabok Part I	914321
279675	Khangabok Pt Ii	591668	Lamding	914315
279676	Khangabok Pt Iii	591645	Khangabok	914316
237694	Khekman	591714	Khekman	269925
237665	Langathel	591648	Langathel	269954
237665	Langathel	591649	Phundrei	269955
237667	Leirongthel Ningel	591652	Chandrakhong	269962
237667	Leirongthel Ningel	591653	Ingourok	269972
237667	Leirongthel Ningel	591650	Kakmayai	269965
237667	Leirongthel Ningel	591654	Khoirom	269971
237667	Leirongthel Ningel	591655	Leirongthel	269964
237667	Leirongthel Ningel	591656	Ningel	269963
237667	Leirongthel Ningel	591657	Phanjangkhong	269961
237695	Leisangthem	591715	Irong Thokchom	269920
237695	Leisangthem	591716	Leisangthem	269922
237695	Leisangthem	591717	Thoudam	269921
237699	Lilong Turel Ahanbi (atoukhong)	591723	Atoukhong	269928
237699	Lilong Turel Ahanbi (atoukhong)	591724	Chaobok	928386
237699	Lilong Turel Ahanbi (atoukhong)	591725	Haoreibi	913737
237699	Lilong Turel Ahanbi (atoukhong)	591726	Lilong	913687
237699	Lilong Turel Ahanbi (atoukhong)	591727	Nungei	269927
237668	Lourembam	591658	Bengi	269942
237668	Lourembam	591659	Icham Khunou	269943
237668	Lourembam	591660	Langmeithel	269967
237668	Lourembam	591661	Lourembam	269966
237668	Lourembam	591662	Pechi	269970
237668	Lourembam	591663	Thokchom	269974
237696	Maibam Uchiwa	591718	Maibam Konjil	269918
237696	Maibam Uchiwa	591719	Uchiwa	269917
237697	Moijing	591720	Moijing	269926
237698	Oinam Sawombung	591721	Laiphrakpam	269930
237698	Oinam Sawombung	591722	Oinam	269929
273100	Samaram	591646	Kang Samaram	913697
273100	Samaram	591647	Khongjom	269958
237670	Sangaiyumpham I	591669	Sangaiyumpham	269946
237669	Sangaiyumpham Pt Ii	591667	Cherapur	269952
237669	Sangaiyumpham Pt Ii	635627	Lamding	269948
237671	Sapam	591670	Chingtham	269959
237671	Sapam	591671	Sapam	269950
237672	Tekcham	591672	Papal	269945
237672	Tekcham	591673	Tekcham	269951
237673	Tentha	591674	Tentha	269947
237674	Wangbal	591675	Kairembikhok	269977
237674	Wangbal	591676	Uyal	269976
237674	Wangbal	591677	Wangbal	269975
237675	Wangjing	591678	Purnaheitupokpi	913699
237675	Wangjing	591679	Wangjing	913700
237676	Wangkhem	591681	Thoubal Khunou	269938
237676	Wangkhem	591682	Wangkhem	269969
237676	Wangkhem	591683	Yaithibi Khunou	913693
"""


lgd_map = {}
with open('/Users/ram/Downloads/09May2024/villages.csv', 'r') as f:
	reader = csv.DictReader(f)
	for r in reader:
		if r['State Name (In English)'] != 'Manipur':
			continue
		lgd_code = r['Village Code']
		lgd_name = r['Village Name (In English)']
		lgd_map[lgd_code] = lgd_name

path = Path('data/lgd_mapping/manipur/mapped_vills/Thoubal/1.csv')
path.parent.mkdir(parents=True, exist_ok=True)
with open(path, 'w') as f:
	wr = csv.writer(f)
	wr.writerow(keys)
	count = 0
	for line in correction_txt.split('\n'):
		if line.strip() == '':
			continue
		count += 1
		parts = line.split('\t')
		lgd_code = parts[-1]
		lgd_name = lgd_map[lgd_code]
		row = [count] + ['Manipur', 'Thoubal', 'Thoubal'] + parts + [lgd_name]
		wr.writerow(row)



