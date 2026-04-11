'use strict';
const MANIFEST = 'flutter-app-manifest';
const TEMP = 'flutter-temp-cache';
const CACHE_NAME = 'flutter-app-cache';

const RESOURCES = {"assets/AssetManifest.bin": "9d8b5eee2c9dfd73097c331e35deae4d",
"assets/AssetManifest.bin.json": "ef17b021a0de9fe8f61eb35861d1bfb5",
"assets/assets/horses_data.json": "2611656c3b4674a8591eaecb4f0bb5b9",
"assets/assets/photos/ajax_photo1.jpeg": "5c959bf7e8269fffed5217fe22334aaf",
"assets/assets/photos/ajax_photo2.jpeg": "3debb00fc50d58ead8629d72fea21063",
"assets/assets/photos/amaris_journey_photo1.jpeg": "6a685b49941a0f4b879037ec1944cabc",
"assets/assets/photos/amaris_journey_photo2.jpeg": "2bfa5930ea05a91d25241a31543ef962",
"assets/assets/photos/angeliques_tigress_warrior_photo1.jpeg": "8ea5268462ed62753f87bfe27900f6a0",
"assets/assets/photos/angeliques_tigress_warrior_photo2.jpeg": "4437612980e4e4f86bfeb7dc7eb56af3",
"assets/assets/photos/anne_bonnys_little_flower_photo1.jpeg": "85be423cf481b0c613c383fb06fac3e2",
"assets/assets/photos/anne_bonnys_little_flower_photo2.jpeg": "fecf92ae267848bca9584dc3aaa03a42",
"assets/assets/photos/anne_bonny_photo1.jpeg": "e78f6796e36d886cb649da7cc6993b7e",
"assets/assets/photos/anne_bonny_photo2.jpeg": "0628e4b5944c0469378a6e31777c180f",
"assets/assets/photos/archers_gambit_photo1.jpeg": "47c7a10d9f39f2278ea03677301b6dd9",
"assets/assets/photos/archers_gambit_photo2.jpeg": "b1d32cf13c467e11d1f34b00da0eba37",
"assets/assets/photos/a_splash_of_freckles_photo1.jpeg": "3ea2dfd5fedc2f405e57c09800dd328f",
"assets/assets/photos/a_splash_of_freckles_photo2.jpeg": "f7d89fac486cf9ec5c3fa2fd2d0d191a",
"assets/assets/photos/badabing_photo1.jpeg": "23863de1e23a3e3c250a90eab4348fb5",
"assets/assets/photos/badabing_photo2.jpeg": "fee6a8fa15735e954c0c0bf1fdb9d685",
"assets/assets/photos/beach_boy_photo1.jpeg": "119db860dbeca56368cd595559e4c755",
"assets/assets/photos/beach_boy_photo2.jpeg": "0d270168f397c6e68a1f14ad5abbd0ec",
"assets/assets/photos/beach_bunny_photo1.jpeg": "95079bda5376802ec9294b7c4578b39b",
"assets/assets/photos/beach_bunny_photo2.jpeg": "e83c9c86ebcaa2df238341f43df2b2de",
"assets/assets/photos/beau_of_artemis_photo1.jpeg": "7688ffe1f19bf183ee5cdae2bcdb8428",
"assets/assets/photos/beau_of_artemis_photo2.jpeg": "5cb2e090ebaa165b7e1ee70a54c91281",
"assets/assets/photos/beebes_perfect_storm_photo1.jpeg": "e51bb9e81d307a3d5067a9a62d73e002",
"assets/assets/photos/beebes_perfect_storm_photo2.jpeg": "2fc20fa7ea980a302a5778bab426ef4b",
"assets/assets/photos/billie_jeans_britches_photo1.jpeg": "d8175c06b712c0c3fb65e808400252b1",
"assets/assets/photos/billie_jeans_britches_photo2.jpeg": "0df58546c8e18be7084ff6f7be1fd904",
"assets/assets/photos/billy_maez_renegade_photo1.jpeg": "faefb947b2e009fa2bb9a7b9f8b6ce55",
"assets/assets/photos/billy_maez_renegade_photo2.jpeg": "2f9f3bd569a0072c8a600bfa8cb37c2c",
"assets/assets/photos/black_pearl_photo1.jpeg": "50aab5553b11f35dceb4028420f95505",
"assets/assets/photos/black_pearl_photo2.jpeg": "03f7b1bf43cce5b236b9cabbba346e7e",
"assets/assets/photos/bonnie_rayes_seaside_dream_photo1.jpeg": "1278d279d7aae65049e6f19f7ea52b4a",
"assets/assets/photos/bonnie_rayes_seaside_dream_photo2.jpeg": "bda5afc4fd1386b43f6fa58c2fcedfe9",
"assets/assets/photos/captain_carltons_martha_lou_photo1.jpeg": "3b0d362044e1973c07f1adfb62a15ca7",
"assets/assets/photos/captain_carltons_martha_lou_photo2.jpeg": "96a9e03cb4bdd7dca53e6f9b826257f3",
"assets/assets/photos/carli_marie_photo1.jpeg": "fdce830a7a37d3948da4d1de8e436f68",
"assets/assets/photos/carli_marie_photo2.jpeg": "661b6167ace3dde04f67078d3b6770fc",
"assets/assets/photos/carollynns_ripple_effect_photo1.jpeg": "883c7f90ad4a9177d9a936108b594db3",
"assets/assets/photos/carollynns_ripple_effect_photo2.jpeg": "3f102d0ae38b8172ec2355df94115d4a",
"assets/assets/photos/catwalks_olympic_glory_photo1.jpeg": "75a30588e176425b6c6b3ad350f458b0",
"assets/assets/photos/catwalks_olympic_glory_photo2.jpeg": "0e7a11cc31eb672fac09e16accee5e5b",
"assets/assets/photos/catwalk_chaos_photo1.jpeg": "a2cb20ca6cd45db267504fa5f7779f9c",
"assets/assets/photos/catwalk_chaos_photo2.jpeg": "a7258fd23daa447bad6ae28a894035a3",
"assets/assets/photos/chers_hope_photo1.jpeg": "bf8e5980f1acd37f62d204d9bd4cfff9",
"assets/assets/photos/chers_hope_photo2.jpeg": "abfef21e6a5e5d062b9be2785d1f8930",
"assets/assets/photos/chickadee_photo1.jpeg": "1581dbb92b1ecfcdd2d4d3712d31f382",
"assets/assets/photos/chickadee_photo2.jpeg": "f06a94cac39d42be76814fc294d8627a",
"assets/assets/photos/chief_golden_eagle_photo1.jpeg": "0cf51b512aa537c2a26127d5a503b47e",
"assets/assets/photos/chief_golden_eagle_photo2.jpeg": "7f80ad9feadadbb9da233b07a945a390",
"assets/assets/photos/chili_photo1.jpeg": "9702743d888ae76e3336e395040c5946",
"assets/assets/photos/chili_photo2.jpeg": "e6ce21d46cf68650ece14968107071cb",
"assets/assets/photos/cj_sammn_photo1.jpeg": "4b1e2d5dd6aef88fc6815108f508eb7e",
"assets/assets/photos/cj_sammn_photo2.jpeg": "0cd9754c1c335a32d37d150adf269220",
"assets/assets/photos/claras_glory_photo1.jpeg": "70fd92e50e324763e2fcf9180fbaa2f9",
"assets/assets/photos/claras_glory_photo2.jpeg": "f906b0aa3cfb6edd7654d9d98d1e6a34",
"assets/assets/photos/clg_apollo_photo1.jpeg": "44a9d101e7dc0eec1175b68a3c1e1e7c",
"assets/assets/photos/clg_apollo_photo2.jpeg": "53b49e2f9c68c6765bd787f129c35e90",
"assets/assets/photos/clg_bay_princess_photo1.jpeg": "ba06538c69fd895c5fd53483f3e3cc58",
"assets/assets/photos/clg_bay_princess_photo2.jpeg": "8af850f6f984a3f26a077665c02b4c49",
"assets/assets/photos/clg_embers_golden_flame_photo1.jpeg": "0c97511dce8e308f71d93dd0eff6d895",
"assets/assets/photos/clg_embers_golden_flame_photo2.jpeg": "5e062baf5dcb85a4c3f85b135900680a",
"assets/assets/photos/clg_magic_moment_photo1.jpeg": "b86550c60e58b44b58c8965a0c0e3f69",
"assets/assets/photos/clg_magic_moment_photo2.jpeg": "57e60c677559aecea01e8e67785b513f",
"assets/assets/photos/clg_mistys_lunar_eclipse_photo1.jpeg": "ab44f34e2f035fe4319452aecc933a4e",
"assets/assets/photos/clg_pennies_from_heaven_photo1.jpeg": "6f09288ec16135a1e2479bafdb0317ec",
"assets/assets/photos/clg_pennies_from_heaven_photo2.jpeg": "de431c20566c390bb86a1013662048d9",
"assets/assets/photos/clg_rider_on_the_storm_photo1.jpeg": "bd25f3dd6f0aaca970c68a506bf939c1",
"assets/assets/photos/clg_rider_on_the_storm_photo2.jpeg": "d488961c55e1e4ab2903a004eb5e673e",
"assets/assets/photos/clg_rumor_has_it_photo1.jpeg": "ddd4a1ab8d7b1de64d4017f7f31909eb",
"assets/assets/photos/clg_rumor_has_it_photo2.jpeg": "90a0a0b3bdf2431ec9c4387512fbd652",
"assets/assets/photos/clg_surfers_blue_moon_photo1.jpeg": "4c30a5dd0ba9c75663f6ca0dea7297f7",
"assets/assets/photos/clg_surfers_blue_moon_photo2.jpeg": "22e4b63e33405bf83b9eea6ac5379ed9",
"assets/assets/photos/clg_tomorrows_tidewater_twist_photo1.jpeg": "17d13a38f35d9032a83db900ee69dde3",
"assets/assets/photos/clg_tomorrows_tidewater_twist_photo2.jpeg": "7b418b6c1accafa3844edd4c6279b091",
"assets/assets/photos/corries_little_miss_magic_photo1.jpeg": "a5809109f4c68c15decb052de49076bf",
"assets/assets/photos/corries_little_miss_magic_photo2.jpeg": "e4b2e17df7d4a933a543031f3667506d",
"assets/assets/photos/courtneys_island_dove_photo1.jpeg": "9fde57a75dc1955b3e06f44c6977e50d",
"assets/assets/photos/courtneys_island_dove_photo2.jpeg": "968ec058e30ac81343f3cbd4cda8386c",
"assets/assets/photos/daisey_photo1.jpeg": "8334dda035e81cfa343c0b9ac1dc6803",
"assets/assets/photos/daisey_photo2.jpeg": "4e9bbba8f97ccc460eaeef11ddeafb33",
"assets/assets/photos/dakota_skys_cody_two_socks_photo1.jpeg": "02dfc2733548fb4bc0dcb658176b1106",
"assets/assets/photos/dakota_skys_cody_two_socks_photo2.jpeg": "929f165994a35cffa842791451ee1215",
"assets/assets/photos/delilahs_sandpiper_photo1.jpeg": "ee843735ea76620aac92515553287298",
"assets/assets/photos/delilahs_sandpiper_photo2.jpeg": "fcc475aaea0d932ac7f2f083d23d0ff8",
"assets/assets/photos/docs_bay_dream_photo1.jpeg": "b11f5cc82236a522af99f0e8fabf03c5",
"assets/assets/photos/docs_bay_dream_photo2.jpeg": "888612e94dc57f400f4082c955ef1d65",
"assets/assets/photos/doctor_amrien_photo1.jpeg": "9ac154569c66734bd2a03612a3c7c9e5",
"assets/assets/photos/doctor_amrien_photo2.jpeg": "989d68a9ab1e8b25a461682621c618ed",
"assets/assets/photos/don_leonard_stud_ii_photo1.jpeg": "3868751ba06cf416f5ace5d4be81544a",
"assets/assets/photos/don_leonard_stud_ii_photo2.jpeg": "12865c8181914a0a32226f39bab1e4e9",
"assets/assets/photos/dreamers_gift_photo1.jpeg": "33303c02cdf0791b153d15524c0927e2",
"assets/assets/photos/dreamers_gift_photo2.jpeg": "87f6fd0159519de857725aac8a489bfb",
"assets/assets/photos/dreamers_stardust_photo1.jpeg": "a5d6573cb83dfcab03372df748aaed1c",
"assets/assets/photos/dreamers_stardust_photo2.jpeg": "ff9cadbe8e698ff230faf43e6f1302a2",
"assets/assets/photos/effies_papa_bear_photo1.jpeg": "554b93e8eca1bb1082d60d011cb70e66",
"assets/assets/photos/effies_papa_bear_photo2.jpeg": "dec851036089ff56189f7403a5a103f3",
"assets/assets/photos/fifteen_friends_of_freckles_photo1.jpeg": "9cd6db4725f444ded85fb4213313cdff",
"assets/assets/photos/fifteen_friends_of_freckles_photo2.jpeg": "e8333410198630d7998bc50e7b709448",
"assets/assets/photos/gidgets_beach_baby_photo1.jpeg": "f05adb4f1b76e393d796bac971fbdd0c",
"assets/assets/photos/gidgets_beach_baby_photo2.jpeg": "8656e6758e6a046ebe3c9714f01b0646",
"assets/assets/photos/good_golly_miss_molly_photo1.jpeg": "83c8fa63820783e47719a64f2fdbaddc",
"assets/assets/photos/good_golly_miss_molly_photo2.jpeg": "a5c7bfd3f4c541ad9737250fc60f6d75",
"assets/assets/photos/gracey_photo1.jpeg": "cc867f2798782cff2f3ce2a23b56b989",
"assets/assets/photos/gracey_photo2.jpeg": "c9bef1e00a6c38af8b8f4b82055394d2",
"assets/assets/photos/grandmas_dream_photo1.jpeg": "5a9ee763bf0f8c512674cc5979704703",
"assets/assets/photos/grandmas_dream_photo2.jpeg": "ec565bdaa3f43fb354cb270c191d231e",
"assets/assets/photos/haldeens_jackpot_photo1.jpeg": "7a49751d1272604e158d872758269475",
"assets/assets/photos/haldeens_jackpot_photo2.jpeg": "716fa41ea331d845316377be4c3511f9",
"assets/assets/photos/heides_sky_photo1.jpeg": "4eebf1e382f8fdd4f1e5e289f887faa8",
"assets/assets/photos/henrys_hidalgo_photo1.jpeg": "aa298fb1fb90ff8b0cc02c6e8991b899",
"assets/assets/photos/henrys_hidalgo_photo2.jpeg": "1f163206862189b4deee24b28e2c7ea7",
"assets/assets/photos/isleros_photo1.jpeg": "dfcc066b2c86e8b4a092709cbe5e8c8f",
"assets/assets/photos/isleros_photo2.jpeg": "fa07b74c78cf901d855235bd7cf99c73",
"assets/assets/photos/jabataa_photo1.jpeg": "be665be959aa7d1578ade2d72b34a301",
"assets/assets/photos/jabataa_photo2.jpeg": "ca9c87e6cc7c54fdd42a962196b6950a",
"assets/assets/photos/jans_little_piece_of_heaven_photo1.jpeg": "a527e2bb2ba562b60bff47561e577566",
"assets/assets/photos/jans_little_piece_of_heaven_photo2.jpeg": "f372d9ff7c447ecdecdb0802919e2618",
"assets/assets/photos/jean_bondes_bayside_angel_photo1.jpeg": "24f3085286278cf270fc9344240c74f5",
"assets/assets/photos/jean_bondes_bayside_angel_photo2.jpeg": "88bc8fa20b56fb44a654b4a2c06d2477",
"assets/assets/photos/jersey_jaxs_photo1.jpeg": "9fb517d9939df1fb52c45e61a31a8fb9",
"assets/assets/photos/jersey_jaxs_photo2.jpeg": "6b952706cc3d35698b0c51914026ac19",
"assets/assets/photos/jessicas_sea_star_sandy_photo1.jpeg": "c944322bcaa2a38c180bfbcb487f6919",
"assets/assets/photos/jessicas_sea_star_sandy_photo2.jpeg": "b2de5de5016efaafb5d7c886e271c2c6",
"assets/assets/photos/jigsaws_little_miss_skeeter_photo1.jpeg": "700793fd06df2f1a5d19af780a11271e",
"assets/assets/photos/jigsaws_little_miss_skeeter_photo2.jpeg": "76641ec6db09d80938e440c4564a7727",
"assets/assets/photos/joes_spirit_photo1.jpeg": "8f95bfc1e9ad7b4d2b2c544d1c4bf226",
"assets/assets/photos/joes_spirit_photo2.jpeg": "017f71fc15e8fb3f10f363be223e8019",
"assets/assets/photos/judys_little_smooch_photo1.jpeg": "85fb52108715a40e3da2a9109ac18ee4",
"assets/assets/photos/judys_little_smooch_photo2.jpeg": "713d815ec8f016f7e8476040888a4db4",
"assets/assets/photos/judys_sunshine_photo1.jpeg": "0673614a2260537cba7ef2efb76f878e",
"assets/assets/photos/judys_sunshine_photo2.jpeg": "0026bc236a745eb552e2103eef477a96",
"assets/assets/photos/kachina_grand_star_photo1.jpeg": "8728de6e96c8655a71d01a8b7f7bda34",
"assets/assets/photos/kachina_grand_star_photo2.jpeg": "2eb9ab1dceb34d733c9cfbb7a8254a9c",
"assets/assets/photos/kachina_mayli_mist_photo1.jpeg": "14643e0b8a8043ae4248bbeadce6975a",
"assets/assets/photos/kachina_mayli_mist_photo2.jpeg": "0261ed6dcddb4cdf8c5314b1d4594958",
"assets/assets/photos/ken_photo1.jpeg": "70a0fb60998f13ddf0c6599c1b885024",
"assets/assets/photos/ken_photo2.jpeg": "6a1009a932e68691a535fb1ea43fd129",
"assets/assets/photos/kimmee-sue_photo1.jpeg": "add1574d416cfe32b4066fe3acf7e2fa",
"assets/assets/photos/kimmee-sue_photo2.jpeg": "a9fee6e4ef528505596bd081d4f04681",
"assets/assets/photos/kismets_velvet_kisses_photo1.jpeg": "d4215ba3f098af3a133001345b0a44de",
"assets/assets/photos/kismets_velvet_kisses_photo2.jpeg": "34ed233c9e60eae669354f98ca421705",
"assets/assets/photos/landis_rjs_jubilation_photo1.jpeg": "ca6789700f271a610d080f13d6b63e26",
"assets/assets/photos/landis_rjs_jubilation_photo2.jpeg": "ca2a2c1779831ea437707f544e3d7b4f",
"assets/assets/photos/little_bit_o_joansie_photo1.jpeg": "f27551dad2011d9923fee80ec9460f30",
"assets/assets/photos/little_bit_o_joansie_photo2.jpeg": "72fdb5096eed20a5f393034322cde9e4",
"assets/assets/photos/little_miss_sunshine_photo1.jpeg": "d5c13e7e1612fdfa85d56e5f708756e8",
"assets/assets/photos/little_miss_sunshine_photo2.jpeg": "51f1a5290062f003d9f5d1503b6396d3",
"assets/assets/photos/lorna_dune_photo1.jpeg": "123f322d964c5fdd73c27d9a05753abe",
"assets/assets/photos/lorna_dune_photo2.jpeg": "6adcda803063b5e6bec44a361c457ab9",
"assets/assets/photos/lovelands_secret_feather_photo1.jpeg": "b5e3e2250ccc1ed13c1af5ebab5708e5",
"assets/assets/photos/lovelands_secret_feather_photo2.jpeg": "ce38cf78a910d4de73072df2c60c7461",
"assets/assets/photos/marguerite_of_chincoteague_photo1.jpeg": "81c5b2c8de05c7cdf6d89b5c1cd17de8",
"assets/assets/photos/marguerite_of_chincoteague_photo2.jpeg": "195b184bf7f558028cb519457dbaefb3",
"assets/assets/photos/marinas_marsh_mallow_photo1.jpeg": "d4dbc29742f898e2571596f5799c8f3f",
"assets/assets/photos/marinas_marsh_mallow_photo2.jpeg": "8e2bdcdb9ca2f3ac3c6b52256b60d2e9",
"assets/assets/photos/marnie_photo1.jpeg": "261c4af9046802a1bb25475a155e3c19",
"assets/assets/photos/marnie_photo2.jpeg": "3ef1576e1747640fce0e8a155c48f884",
"assets/assets/photos/mary_read_photo1.jpeg": "f55783ad2d17e7b111cd216f38502df3",
"assets/assets/photos/mary_read_photo2.jpeg": "5301b1145bf87c25bb4004af8b13b8de",
"assets/assets/photos/maverick_photo1.jpeg": "b0e6e1d28df3521695ef81f65808a75b",
"assets/assets/photos/maverick_photo2.jpeg": "f7ccc58ed2fe73577c6eab845b9ed727",
"assets/assets/photos/mays_grand_slam_photo1.jpeg": "34643d398aaa95c34ca9a47d4ce050ad",
"assets/assets/photos/mays_grand_slam_photo2.jpeg": "84c643d5c9c9b2227e6b46cabbba099a",
"assets/assets/photos/milly_sue_photo1.jpeg": "409b2db3f322e01c8f04f3fa96bd6b03",
"assets/assets/photos/milly_sue_photo2.jpeg": "10869aca297e8f24d0f35e5525eaf828",
"assets/assets/photos/mimis_bayside_bella_photo1.jpeg": "b9f20053f2f840bd411603b94914449a",
"assets/assets/photos/mimis_bayside_bella_photo2.jpeg": "b7e6c34931e9b005eac87d703abd7abe",
"assets/assets/photos/miracles_natural_beauty_photo1.jpeg": "fde2eab284b6391b657d7daa6e2bae62",
"assets/assets/photos/miracles_natural_beauty_photo2.jpeg": "b33917366819f48d7b9aa1fa796c1301",
"assets/assets/photos/missme_photo1.jpeg": "a794ae44d6035f47ef0d4e302e5cb8b9",
"assets/assets/photos/missme_photo2.jpeg": "7bf3d3948ce82d3ce2770419c9aa84b2",
"assets/assets/photos/miss_admiral_halsey_photo1.jpeg": "c8f4c01012e1f9afd4df82dd1fe2077a",
"assets/assets/photos/miss_admiral_halsey_photo2.jpeg": "1132526b5cafe1e4e30c2c6cc0722b63",
"assets/assets/photos/miss_holy_smokes_photo1.jpeg": "ea31d25d22c4904e275508df40eefe26",
"assets/assets/photos/miss_holy_smokes_photo2.jpeg": "31e35a16f53c6fd4324ae3e99220fcee",
"assets/assets/photos/misty_mills_photo1.jpeg": "5a30ee7fdeb092358a6cfdd5842a2d8b",
"assets/assets/photos/misty_mills_photo2.jpeg": "d3b1718af8f8ba4295b4df79091aad18",
"assets/assets/photos/mitzi_jo_photo1.jpeg": "aee6d0e7416703bf8992f38fa0173677",
"assets/assets/photos/mitzi_jo_photo2.jpeg": "d13eb433da4496f51e03dc353bbf6e83",
"assets/assets/photos/mollys_rosebud_photo1.jpeg": "ec804514160d19c47234f75ce69e237f",
"assets/assets/photos/ms_shampine_photo1.jpeg": "48105d1f7f94fe3cd45387d4b2d9908c",
"assets/assets/photos/ms_shampine_photo2.jpeg": "e8be0e574f66fbb65c63dae04db056f0",
"assets/assets/photos/myrt_brendas_indiana_girl_photo1.jpeg": "eca04e21349aca55fa4c8341294e120a",
"assets/assets/photos/myrt_brendas_indiana_girl_photo2.jpeg": "0040c2c9c87a7cc780674a0549433bec",
"assets/assets/photos/mz_peg_photo1.jpeg": "2b1b53c8fcb1910eaf0c04af3bd0adf2",
"assets/assets/photos/mz_peg_photo2.jpeg": "dc61679582881304d12358ab6e459fff",
"assets/assets/photos/norman_rockwell_giddings_photo1.jpeg": "b04096a6bb068c1bac0dc1079c240f66",
"assets/assets/photos/norman_rockwell_giddings_photo2.jpeg": "d41adc543df6dc61b3f99f8159c56cd4",
"assets/assets/photos/norms_princess_bella_photo1.jpeg": "f1bfd4d6b00540bd8e44cfb007b3b163",
"assets/assets/photos/norms_princess_bella_photo2.jpeg": "3135b120f2a01f76f4ce0e2b378e8a19",
"assets/assets/photos/pappys_pony_photo1.jpeg": "c7195824f76cbea876bc55658b466922",
"assets/assets/photos/pappys_pony_photo2.jpeg": "9d747caca36f1f20fa7511cefc381bfc",
"assets/assets/photos/penny_lane_photo1.jpeg": "66760754c3053bd851ee38373726c34a",
"assets/assets/photos/penny_lane_photo2.jpeg": "58ba49b352994885f8f8e56c35fadab9",
"assets/assets/photos/pony_girls_bliss_photo1.jpeg": "ff3692499361173ab4d5c64e000ca6b1",
"assets/assets/photos/pony_girls_bliss_photo2.jpeg": "8f675dcbd2561af8f46025ad26b31e72",
"assets/assets/photos/poseidons_triton_photo1.jpeg": "0109fe824e50929f45e1eede28fec442",
"assets/assets/photos/poseidons_triton_photo2.jpeg": "2c992c4fe9500127c30ff48820ac766d",
"assets/assets/photos/precious_jewel_photo1.jpeg": "c67eb72c0e786c4827dbf54a492f0a20",
"assets/assets/photos/precious_jewel_photo2.jpeg": "b0c957cfad2f2ed059548d80114e3513",
"assets/assets/photos/randy_photo1.jpeg": "314da104ac23edcab4d0bd6b38dfc41b",
"assets/assets/photos/randy_photo2.jpeg": "eb95742d5dbf64321b102b99ba8c854f",
"assets/assets/photos/roberta_rayes_seaside_dream_photo1.jpeg": "44b770fa0879c08a6d3f8a5fc88efa4a",
"assets/assets/photos/roberta_rayes_seaside_dream_photo2.jpeg": "559cfdcaf4de5ace8d50e484c5751534",
"assets/assets/photos/rosies_teapot_photo1.jpeg": "bad6ce3ea1de353aab454910b7191aaa",
"assets/assets/photos/rosies_teapot_photo2.jpeg": "723a62d76767205c4d745d2322be0602",
"assets/assets/photos/rylees_way_photo1.jpeg": "a741331ced2fd0809cb736712d1ae93a",
"assets/assets/photos/rylees_way_photo2.jpeg": "bdc7b10aa5c55d6feefd348cc3ec77e0",
"assets/assets/photos/scarletts_little_bee_photo1.jpeg": "91592c309e54e5c9ea206db8d1bcd54e",
"assets/assets/photos/scarletts_little_bee_photo2.jpeg": "c2656c209965cbbb772f1e0dc524a70f",
"assets/assets/photos/scc_aurora_photo1.jpeg": "9b60409f06a4675cca0e696fc109de0f",
"assets/assets/photos/scc_aurora_photo2.jpeg": "89501468cc6a039921a03821d5c10c47",
"assets/assets/photos/scc_mistys_sunburst_photo1.jpeg": "c3e956c015bdede662c3b39a695455ab",
"assets/assets/photos/scc_mistys_sunburst_photo2.jpeg": "3bc7179b5d6b5f3c29882600748a91be",
"assets/assets/photos/scc_surfers_point_break_photo1.jpeg": "abf7b590995888ae3b45551d8d570c06",
"assets/assets/photos/scc_surfers_point_break_photo2.jpeg": "9c5e67175e52f415dacf2395d1df3269",
"assets/assets/photos/seaside_miracle_photo1.jpeg": "51890531383e07e2de8df9be9593ab70",
"assets/assets/photos/seaside_miracle_photo2.jpeg": "f5896aad49c23cc1fa2bc2e697c8f9c3",
"assets/assets/photos/serendipity_photo1.jpeg": "42a85fab26101b31fed320b32efbfef2",
"assets/assets/photos/serendipity_photo2.jpeg": "f4c4f8fab4abc3aca33b0a88b6c3358a",
"assets/assets/photos/shelleys_shell_search_photo1.jpeg": "e4e6917b6c16bfa2d457ba0400ed5a7a",
"assets/assets/photos/shelleys_shell_search_photo2.jpeg": "417101b323ebe77ce7c849001652373e",
"assets/assets/photos/shy_sassy_sweet_lady_suede_photo1.jpeg": "9e652403e73d475c7e0cc6838920ae55",
"assets/assets/photos/shy_sassy_sweet_lady_suede_photo2.jpeg": "afe2b6f5a36cdbfdf075da0183751853",
"assets/assets/photos/skylark_photo1.jpeg": "7ef8cd899856456a67d735ba40b44464",
"assets/assets/photos/skylark_photo2.jpeg": "eac517f5660e009e72a006b080ad0aa0",
"assets/assets/photos/sky_dancer_photo1.jpeg": "6fbb75e57cf0d0fac2a1deb1b7f73997",
"assets/assets/photos/sky_dancer_photo2.jpeg": "6f442d0f5e2c549230aa9ba78d0ba5aa",
"assets/assets/photos/splash_photo1.jpeg": "409fd8f35f24db5f03881bfec49d5748",
"assets/assets/photos/splash_photo2.jpeg": "7b9b08302d3cae54cba7eadf4032c4a6",
"assets/assets/photos/sues_crown_of_hope_photo1.jpeg": "d8a9bed18f0ac5751e5bd050ce68f622",
"assets/assets/photos/sues_crown_of_hope_photo2.jpeg": "d3d673daed6c7bbaf45c92bcf2bb6aa7",
"assets/assets/photos/summer_breeze_photo1.jpeg": "cb36c6a9f4bcd97e965283c01958ad6f",
"assets/assets/photos/summer_breeze_photo2.jpeg": "85370cbeeb725bd41ce75ea976accad3",
"assets/assets/photos/sunny_skies_after_the_storm_photo1.jpeg": "48a0972d652ba32689432216be9159e7",
"assets/assets/photos/sunny_skies_after_the_storm_photo2.jpeg": "7d1222439c1b7e63a1d10ae87da3066e",
"assets/assets/photos/sunrise_ocean_tides_photo1.jpeg": "87f399f6f55b30deda0c7aeabc908e5e",
"assets/assets/photos/sunrise_ocean_tides_photo2.jpeg": "4d80e55d2efbc4e637458b585ca545f7",
"assets/assets/photos/surfers_riptide_photo1.jpeg": "bb474c44f88e6341fbaa23565e7610ab",
"assets/assets/photos/surfers_riptide_photo2.jpeg": "1760382fefaaf752ca23f354cde59051",
"assets/assets/photos/surfers_shining_star_photo1.jpeg": "2b496bc1582705d9db9030f6da838128",
"assets/assets/photos/surfers_shining_star_photo2.jpeg": "d1cc79f35fb8f0ad80bb2e11522ea2aa",
"assets/assets/photos/surfer_princess_photo1.jpeg": "b7b126cc009af2daf5a940d443d67e94",
"assets/assets/photos/surfer_princess_photo2.jpeg": "50cedc6df0319b75f8100c32e4c9fd7f",
"assets/assets/photos/surfette_photo1.jpeg": "cedfa55144b88ad8b600a7508dc29cbf",
"assets/assets/photos/surfette_photo2.jpeg": "d304b6cc5907be607104c0b89ba62b2b",
"assets/assets/photos/surfin_chantel_photo1.jpeg": "efbef2b76ce438768194295a0f975f77",
"assets/assets/photos/surfin_chantel_photo2.jpeg": "17f9e69773ea0089ec3188ea50e9c02f",
"assets/assets/photos/sweetheart_photo1.jpeg": "dacc6718574772a234eb8f77ba88d87a",
"assets/assets/photos/sweetheart_photo2.jpeg": "cc148cc9ed0c2b60f90b8c120f223d48",
"assets/assets/photos/taliaevans_angel_photo1.jpeg": "876be3f1b482d3122b5724d0ff98fae0",
"assets/assets/photos/taliaevans_angel_photo2.jpeg": "97f5009f2f43b36bf04c8922e74e33e2",
"assets/assets/photos/tawny_treasure_photo1.jpeg": "276b166e56a5352466c44cf7e036e82b",
"assets/assets/photos/tawny_treasure_photo2.jpeg": "45e2c582fcfe27c3ecd04ccd5acad236",
"assets/assets/photos/thunderbolt_photo1.jpeg": "552607adbbeef00c2d4f63143f89c6e6",
"assets/assets/photos/thunderbolt_photo2.jpeg": "3e36af7642524261c5f544a55f940468",
"assets/assets/photos/thunderstorm_skies_photo1.jpeg": "77dde20a4f5cae35eb39023080653016",
"assets/assets/photos/thunderstorm_skies_photo2.jpeg": "2ab9db0bdbad3ec456fbf1af2ecced1a",
"assets/assets/photos/tornados_legacy_photo1.jpeg": "9708e0d44b9c98a824f4a5d18bfd7b4b",
"assets/assets/photos/tornados_legacy_photo2.jpeg": "bb01d06d56843a372e03523a44d5bcb2",
"assets/assets/photos/tornados_prince_of_tides_photo1.jpeg": "2e4f609b1b48e8a279c50f22820c24ba",
"assets/assets/photos/tornados_prince_of_tides_photo2.jpeg": "d2e7cee12b0144140c565ffcad13cde1",
"assets/assets/photos/treasures_reflection_of_ace_photo1.jpeg": "0e51794dd3375ef9431c6ee89d4b69a7",
"assets/assets/photos/treasures_reflection_of_ace_photo2.jpeg": "5fa4759dd21d91dab85fbaad0a2f79c2",
"assets/assets/photos/tunie_photo1.jpeg": "ad9e5c1c3305d5446da5c4b9ecda2f48",
"assets/assets/photos/tunie_photo2.jpeg": "28832c377bbb08eba8e7a9725322e4ff",
"assets/assets/photos/two_teagues_golden_girl_died_jan_2026_photo1.jpeg": "4311f19ca17eba7241a4033ca5dbe81a",
"assets/assets/photos/two_teagues_golden_girl_died_jan_2026_photo2.jpeg": "18f0d9b844c642999a2a2c3439c0f8ff",
"assets/assets/photos/two_teagues_tacos_chilibean_photo1.jpeg": "94f21fed11bf004d3d8d99c6ffbb0aee",
"assets/assets/photos/two_teagues_tacos_chilibean_photo2.jpeg": "b55bcd48c488acd2c53e76d70ef71350",
"assets/assets/photos/two_teagues_taco_photo1.jpeg": "3b205c0e29f781f82d3e81abc4e103f8",
"assets/assets/photos/two_teagues_taco_photo2.jpeg": "a806af09b4f3e6e797faaa5a67d32e68",
"assets/assets/photos/wendys_carolina_girl_photo1.jpeg": "c0a86fe603a9f0717718be51b2334492",
"assets/assets/photos/wendys_carolina_girl_photo2.jpeg": "9ba4cd4aa4b292877469b1358078411a",
"assets/assets/photos/white_saddle_photo1.jpeg": "e258adf1da58767d3a1fcbae62b9acab",
"assets/assets/photos/white_saddle_photo2.jpeg": "a45eec3ed742e2d970e5b8b04cacb368",
"assets/assets/photos/wildest_dreams_photo1.jpeg": "ce647d14e91646f013c78e71b3b59db6",
"assets/assets/photos/wildest_dreams_photo2.jpeg": "a3e9adb601773652828a21e3f4aeae0b",
"assets/assets/photos/wildfires_phoenix_photo1.jpeg": "1fba38cbcbdcdfee0f26315255224ba4",
"assets/assets/photos/wildfires_phoenix_photo2.jpeg": "3b70d87a80f91fc9ddfb631d7ab2d92d",
"assets/assets/photos/winter_moon_photo1.jpeg": "2dce3fd7a371ffe9e1c29af9d7d36fb9",
"assets/FontManifest.json": "dc3d03800ccca4601324923c0b1d6d57",
"assets/fonts/MaterialIcons-Regular.otf": "4b122b3d076edc2c493867db6e468253",
"assets/NOTICES": "f75c9a68367800c2ebe79883823b12ed",
"assets/packages/cupertino_icons/assets/CupertinoIcons.ttf": "33b7d9392238c04c131b6ce224e13711",
"assets/shaders/ink_sparkle.frag": "ecc85a2e95f5e9f53123dcaf8cb9b6ce",
"assets/shaders/stretch_effect.frag": "40d68efbbf360632f614c731219e95f0",
"canvaskit/canvaskit.js": "8331fe38e66b3a898c4f37648aaf7ee2",
"canvaskit/canvaskit.js.symbols": "a3c9f77715b642d0437d9c275caba91e",
"canvaskit/canvaskit.wasm": "9b6a7830bf26959b200594729d73538e",
"canvaskit/chromium/canvaskit.js": "a80c765aaa8af8645c9fb1aae53f9abf",
"canvaskit/chromium/canvaskit.js.symbols": "e2d09f0e434bc118bf67dae526737d07",
"canvaskit/chromium/canvaskit.wasm": "a726e3f75a84fcdf495a15817c63a35d",
"canvaskit/skwasm.js": "8060d46e9a4901ca9991edd3a26be4f0",
"canvaskit/skwasm.js.symbols": "3a4aadf4e8141f284bd524976b1d6bdc",
"canvaskit/skwasm.wasm": "7e5f3afdd3b0747a1fd4517cea239898",
"canvaskit/skwasm_heavy.js": "740d43a6b8240ef9e23eed8c48840da4",
"canvaskit/skwasm_heavy.js.symbols": "0755b4fb399918388d71b59ad390b055",
"canvaskit/skwasm_heavy.wasm": "b0be7910760d205ea4e011458df6ee01",
"favicon.png": "5dcef449791fa27946b3d35ad8803796",
"flutter.js": "24bc71911b75b5f8135c949e27a2984e",
"flutter_bootstrap.js": "8a3f881dc2e3f48f52b1379c23b7beac",
"icons/Icon-192.png": "ac9a721a12bbc803b44f645561ecb1e1",
"icons/Icon-512.png": "96e752610906ba2a93c65f8abe1645f1",
"icons/Icon-maskable-192.png": "c457ef57daa1d16f64b27b786ec2ea3c",
"icons/Icon-maskable-512.png": "301a7604d45b3e739efc881eb04896ea",
"index.html": "837fec60a46f507d8e9d3af9e061ef73",
"/": "837fec60a46f507d8e9d3af9e061ef73",
"main.dart.js": "df9d96f223a8533111b91da572169d34",
"manifest.json": "aa41ec71be71259c62627bbc3b68b407",
"version.json": "b3c230beecac6154b9e589d77313ffa9"};
// The application shell files that are downloaded before a service worker can
// start.
const CORE = ["main.dart.js",
"index.html",
"flutter_bootstrap.js",
"assets/AssetManifest.bin.json",
"assets/FontManifest.json"];

// During install, the TEMP cache is populated with the application shell files.
self.addEventListener("install", (event) => {
  self.skipWaiting();
  return event.waitUntil(
    caches.open(TEMP).then((cache) => {
      return cache.addAll(
        CORE.map((value) => new Request(value, {'cache': 'reload'})));
    })
  );
});
// During activate, the cache is populated with the temp files downloaded in
// install. If this service worker is upgrading from one with a saved
// MANIFEST, then use this to retain unchanged resource files.
self.addEventListener("activate", function(event) {
  return event.waitUntil(async function() {
    try {
      var contentCache = await caches.open(CACHE_NAME);
      var tempCache = await caches.open(TEMP);
      var manifestCache = await caches.open(MANIFEST);
      var manifest = await manifestCache.match('manifest');
      // When there is no prior manifest, clear the entire cache.
      if (!manifest) {
        await caches.delete(CACHE_NAME);
        contentCache = await caches.open(CACHE_NAME);
        for (var request of await tempCache.keys()) {
          var response = await tempCache.match(request);
          await contentCache.put(request, response);
        }
        await caches.delete(TEMP);
        // Save the manifest to make future upgrades efficient.
        await manifestCache.put('manifest', new Response(JSON.stringify(RESOURCES)));
        // Claim client to enable caching on first launch
        self.clients.claim();
        return;
      }
      var oldManifest = await manifest.json();
      var origin = self.location.origin;
      for (var request of await contentCache.keys()) {
        var key = request.url.substring(origin.length + 1);
        if (key == "") {
          key = "/";
        }
        // If a resource from the old manifest is not in the new cache, or if
        // the MD5 sum has changed, delete it. Otherwise the resource is left
        // in the cache and can be reused by the new service worker.
        if (!RESOURCES[key] || RESOURCES[key] != oldManifest[key]) {
          await contentCache.delete(request);
        }
      }
      // Populate the cache with the app shell TEMP files, potentially overwriting
      // cache files preserved above.
      for (var request of await tempCache.keys()) {
        var response = await tempCache.match(request);
        await contentCache.put(request, response);
      }
      await caches.delete(TEMP);
      // Save the manifest to make future upgrades efficient.
      await manifestCache.put('manifest', new Response(JSON.stringify(RESOURCES)));
      // Claim client to enable caching on first launch
      self.clients.claim();
      return;
    } catch (err) {
      // On an unhandled exception the state of the cache cannot be guaranteed.
      console.error('Failed to upgrade service worker: ' + err);
      await caches.delete(CACHE_NAME);
      await caches.delete(TEMP);
      await caches.delete(MANIFEST);
    }
  }());
});
// The fetch handler redirects requests for RESOURCE files to the service
// worker cache.
self.addEventListener("fetch", (event) => {
  if (event.request.method !== 'GET') {
    return;
  }
  var origin = self.location.origin;
  var key = event.request.url.substring(origin.length + 1);
  // Redirect URLs to the index.html
  if (key.indexOf('?v=') != -1) {
    key = key.split('?v=')[0];
  }
  if (event.request.url == origin || event.request.url.startsWith(origin + '/#') || key == '') {
    key = '/';
  }
  // If the URL is not the RESOURCE list then return to signal that the
  // browser should take over.
  if (!RESOURCES[key]) {
    return;
  }
  // If the URL is the index.html, perform an online-first request.
  if (key == '/') {
    return onlineFirst(event);
  }
  event.respondWith(caches.open(CACHE_NAME)
    .then((cache) =>  {
      return cache.match(event.request).then((response) => {
        // Either respond with the cached resource, or perform a fetch and
        // lazily populate the cache only if the resource was successfully fetched.
        return response || fetch(event.request).then((response) => {
          if (response && Boolean(response.ok)) {
            cache.put(event.request, response.clone());
          }
          return response;
        });
      })
    })
  );
});
self.addEventListener('message', (event) => {
  // SkipWaiting can be used to immediately activate a waiting service worker.
  // This will also require a page refresh triggered by the main worker.
  if (event.data === 'skipWaiting') {
    self.skipWaiting();
    return;
  }
  if (event.data === 'downloadOffline') {
    downloadOffline();
    return;
  }
});
// Download offline will check the RESOURCES for all files not in the cache
// and populate them.
async function downloadOffline() {
  var resources = [];
  var contentCache = await caches.open(CACHE_NAME);
  var currentContent = {};
  for (var request of await contentCache.keys()) {
    var key = request.url.substring(origin.length + 1);
    if (key == "") {
      key = "/";
    }
    currentContent[key] = true;
  }
  for (var resourceKey of Object.keys(RESOURCES)) {
    if (!currentContent[resourceKey]) {
      resources.push(resourceKey);
    }
  }
  return contentCache.addAll(resources);
}
// Attempt to download the resource online before falling back to
// the offline cache.
function onlineFirst(event) {
  return event.respondWith(
    fetch(event.request).then((response) => {
      return caches.open(CACHE_NAME).then((cache) => {
        cache.put(event.request, response.clone());
        return response;
      });
    }).catch((error) => {
      return caches.open(CACHE_NAME).then((cache) => {
        return cache.match(event.request).then((response) => {
          if (response != null) {
            return response;
          }
          throw error;
        });
      });
    })
  );
}
