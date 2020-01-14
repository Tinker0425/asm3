
import asm3.additional
import asm3.animal
import asm3.animalcontrol
import asm3.clinic
import asm3.configuration
import asm3.financial
import asm3.html
import asm3.log
import asm3.lookups
import asm3.lostfound
import asm3.media
import asm3.medical
import asm3.movement
import asm3.person
import asm3.publishers.base
import asm3.template
import asm3.users
import asm3.utils
import asm3.waitinglist
from asm3.i18n import _, format_currency_no_symbol, format_time, now, python2display, yes_no

import zipfile

def org_tags(dbo, username):
    """
    Generates a list of tags from the organisation and user info
    """
    u = asm3.users.get_users(dbo, username)
    realname = ""
    email = ""
    sig = ""
    if len(u) > 0:
        u = u[0]
        realname = asm3.utils.nulltostr(u["REALNAME"])
        email = asm3.utils.nulltostr(u["EMAILADDRESS"])
        sig = asm3.utils.nulltostr(u["SIGNATURE"])
    orgname = asm3.configuration.organisation(dbo)
    orgaddress = asm3.configuration.organisation_address(dbo)
    orgtown = asm3.configuration.organisation_town(dbo)
    orgcounty = asm3.configuration.organisation_county(dbo)
    orgpostcode = asm3.configuration.organisation_postcode(dbo)
    orgtel = asm3.configuration.organisation_telephone(dbo)
    tags = {
        "ORGANISATION"          : orgname,
        "ORGANISATIONADDRESS"   : orgaddress,
        "ORGANISATIONTOWN"      : orgtown,
        "ORGANISATIONCOUNTY"    : orgcounty,
        "ORGANISATIONPOSTCODE"  : orgpostcode,
        "ORGANISATIONTELEPHONE" : orgtel,
        "ORGANIZATION"          : orgname,
        "ORGANIZATIONADDRESS"   : orgaddress,
        "ORGANIZATIONCITY"      : orgtown,
        "ORGANIZATIONSTATE"     : orgcounty,
        "ORGANIZATIONZIPCODE"   : orgpostcode,
        "ORGANIZATIONTELEPHONE" : orgtel,
        "DATE"                  : python2display(dbo.locale, now(dbo.timezone)),
        "USERNAME"              : username,
        "USERREALNAME"          : realname,
        "USEREMAILADDRESS"      : email,
        "USERSIGNATURE"         : "<img src=\"" + sig + "\" >",
        "USERSIGNATURESRC"      : sig
    }
    return tags

def additional_yesno(l, af):
    """
    Returns the yes/no value for an additional field. If it has a LOOKUPVALUES
    set, we use the value the user set.
    """
    if af["LOOKUPVALUES"] is not None and af["LOOKUPVALUES"].strip() != "":
        values = af["LOOKUPVALUES"].split("|")
        for v in values:
            if af["VALUE"] is None:
                if v.strip().startswith("0"):
                    return v[v.find("=")+1:]
            else:
                if v.strip().startswith(af["VALUE"]):
                    return v[v.find("=")+1:]
    else:
        return yes_no(l, af["VALUE"] == "1")

def weight_display(dbo, wv):
    """ formats the weight value wv for display (either kg or lb/oz) """
    kg = asm3.utils.cfloat(wv)
    lb = asm3.utils.cint(wv)
    oz = asm3.utils.cint((kg - lb) * 16.0)
    l = dbo.locale
    if asm3.configuration.show_weight_in_lbs(dbo):
        return "%s %s %s %s" % ( lb, _("lb", l), oz, _("oz", l) )
    else:
        return "%s %s" % (kg, _("kg", l))

def br(s):
    """ Returns s with linebreaks turned to <br/> tags """
    if s is None: return ""
    s = s.replace("\r\n", "<br/>").replace("\n", "<br/>")
    return s

def fw(s):
    """ Returns the first word of a string """
    if s is None: return ""
    if s.find(" ") == -1: return s
    return s.split(" ")[0]

def additional_field_tags(dbo, fields, prefix = ""):
    """ Process additional fields and returns them as tags """
    l = dbo.locale
    tags = {}
    for af in fields:
        val = af["VALUE"]
        if val is None: val = ""
        if af["FIELDTYPE"] == asm3.additional.YESNO:
            val = additional_yesno(l, af)
        if af["FIELDTYPE"] == asm3.additional.MONEY:
            val = format_currency_no_symbol(l, af["VALUE"])
        if af["FIELDTYPE"] == asm3.additional.ANIMAL_LOOKUP:
            val = af["ANIMALNAME"]
        if af["FIELDTYPE"] == asm3.additional.PERSON_LOOKUP:
            val = af["OWNERNAME"]
        tags[prefix + af["FIELDNAME"].upper()] = val
    return tags

def animal_tags_publisher(dbo, a, includeAdditional=True):
    """
    Convenience method for getting animal tags when used by a publisher - 
    very little apart from additional fields are required and we can save
    database calls for each asm3.animal.
    """
    return animal_tags(dbo, a, includeAdditional=includeAdditional, includeCosts=False, includeDiet=True, \
        includeDonations=False, includeFutureOwner=False, includeIsVaccinated=True, includeLogs=False, includeMedical=False, includeTransport=False)

def animal_tags(dbo, a, includeAdditional=True, includeCosts=True, includeDiet=True, includeDonations=True, \
        includeFutureOwner=True, includeIsVaccinated=True, includeLogs=True, includeMedical=True, includeTransport=True):
    """
    Generates a list of tags from an animal result (the deep type from
    calling asm3.animal.get_animal)
    includeAdoptionStatus in particular is expensive. If you don't need some of the tags, you can not include them.
    """
    l = dbo.locale
    animalage = a["ANIMALAGE"]
    if animalage and animalage.endswith("."): 
        animalage = animalage[0:len(animalage)-1]
    timeonshelter = a["TIMEONSHELTER"]
    if timeonshelter and timeonshelter.endswith("."): 
        timeonshelter = timeonshelter[0:len(timeonshelter)-1]
    displaydob = python2display(l, a["DATEOFBIRTH"])
    displayage = animalage
    estimate = ""
    if a["ESTIMATEDDOB"] == 1: 
        displaydob = a["AGEGROUP"]
        displayage = a["AGEGROUP"]
        estimate = _("estimate", l)

    tags = { 
        "ANIMALNAME"            : a["ANIMALNAME"],
        "ANIMALTYPENAME"        : a["ANIMALTYPENAME"],
        "BASECOLOURNAME"        : a["BASECOLOURNAME"],
        "BASECOLORNAME"         : a["BASECOLOURNAME"],
        "BREEDNAME"             : a["BREEDNAME"],
        "INTERNALLOCATION"      : a["SHELTERLOCATIONNAME"],
        "LOCATIONNAME"          : a["SHELTERLOCATIONNAME"],
        "LOCATIONDESCRIPTION"   : a["SHELTERLOCATIONDESCRIPTION"],
        "LOCATIONUNIT"          : a["SHELTERLOCATIONUNIT"],
        "DISPLAYLOCATION"       : a["DISPLAYLOCATION"],
        "COATTYPE"              : a["COATTYPENAME"],
        "HEALTHPROBLEMS"        : a["HEALTHPROBLEMS"],
        "HEALTHPROBLEMSBR"      : br(a["HEALTHPROBLEMS"]),
        "ANIMALCREATEDBY"       : a["CREATEDBY"],
        "ANIMALCREATEDDATE"     : python2display(l, a["CREATEDDATE"]),
        "DATEBROUGHTIN"         : python2display(l, a["DATEBROUGHTIN"]),
        "TIMEBROUGHTIN"         : format_time(a["DATEBROUGHTIN"]),
        "DATEOFBIRTH"           : python2display(l, a["DATEOFBIRTH"]),
        "AGEGROUP"              : a["AGEGROUP"],
        "DISPLAYDOB"            : displaydob,
        "DISPLAYAGE"            : displayage,
        "ESTIMATEDDOB"          : estimate,
        "HOLDUNTILDATE"         : python2display(l, a["HOLDUNTILDATE"]),
        "ANIMALID"              : str(a["ID"]),
        "FEE"                   : format_currency_no_symbol(l, a["FEE"]),
        "IDENTICHIPNUMBER"      : a["IDENTICHIPNUMBER"],
        "IDENTICHIPPED"         : a["IDENTICHIPPEDNAME"],
        "IDENTICHIPPEDDATE"     : python2display(l, a["IDENTICHIPDATE"]),
        "MICROCHIPNUMBER"       : a["IDENTICHIPNUMBER"],
        "MICROCHIPNUMBER2"      : a["IDENTICHIP2NUMBER"],
        "MICROCHIPPED"          : a["IDENTICHIPPEDNAME"],
        "MICROCHIPDATE"         : python2display(l, a["IDENTICHIPDATE"]),
        "MICROCHIPDATE2"        : python2display(l, a["IDENTICHIP2DATE"]),
        "MICROCHIPMANUFACTURER" : asm3.lookups.get_microchip_manufacturer(l, a["IDENTICHIPNUMBER"]),
        "MICROCHIPMANUFACTURER2": asm3.lookups.get_microchip_manufacturer(l, a["IDENTICHIP2NUMBER"]),
        "TATTOO"                : a["TATTOONAME"],
        "TATTOODATE"            : python2display(l, a["TATTOODATE"]),
        "TATTOONUMBER"          : a["TATTOONUMBER"],
        "COMBITESTED"           : a["COMBITESTEDNAME"],
        "FIVLTESTED"            : a["COMBITESTEDNAME"],
        "COMBITESTDATE"         : asm3.utils.iif(a["COMBITESTED"] == 1, python2display(l, a["COMBITESTDATE"]), ""),
        "FIVLTESTDATE"          : asm3.utils.iif(a["COMBITESTED"] == 1, python2display(l, a["COMBITESTDATE"]), ""),
        "COMBITESTRESULT"       : asm3.utils.iif(a["COMBITESTED"] == 1, a["COMBITESTRESULTNAME"], ""),
        "FIVTESTRESULT"         : asm3.utils.iif(a["COMBITESTED"] == 1, a["COMBITESTRESULTNAME"], ""),
        "FIVRESULT"             : asm3.utils.iif(a["COMBITESTED"] == 1, a["COMBITESTRESULTNAME"], ""),
        "FLVTESTRESULT"         : asm3.utils.iif(a["COMBITESTED"] == 1, a["FLVRESULTNAME"], ""),
        "FLVRESULT"             : asm3.utils.iif(a["COMBITESTED"] == 1, a["FLVRESULTNAME"], ""),
        "HEARTWORMTESTED"       : a["HEARTWORMTESTEDNAME"],
        "HEARTWORMTESTDATE"     : asm3.utils.iif(a["HEARTWORMTESTED"] == 1, python2display(l, a["HEARTWORMTESTDATE"]), ""),
        "HEARTWORMTESTRESULT"   : asm3.utils.iif(a["HEARTWORMTESTED"] == 1, a["HEARTWORMTESTRESULTNAME"], ""),
        "HIDDENCOMMENTS"        : a["HIDDENANIMALDETAILS"],
        "HIDDENCOMMENTSBR"      : br(a["HIDDENANIMALDETAILS"]),
        "HIDDENANIMALDETAILS"   : a["HIDDENANIMALDETAILS"],
        "HIDDENANIMALDETAILSBR" : br(a["HIDDENANIMALDETAILS"]),
        "ANIMALLASTCHANGEDBY"   : a["LASTCHANGEDBY"],
        "ANIMALLASTCHANGEDDATE" : python2display(l, a["LASTCHANGEDDATE"]),
        "MARKINGS"              : a["MARKINGS"],
        "MARKINGSBR"            : br(a["MARKINGS"]),
        "DECLAWED"              : a["DECLAWEDNAME"],
        "RABIESTAG"             : a["RABIESTAG"],
        "GOODWITHCATS"          : a["ISGOODWITHCATSNAME"],
        "GOODWITHDOGS"          : a["ISGOODWITHDOGSNAME"],
        "GOODWITHCHILDREN"      : a["ISGOODWITHCHILDRENNAME"],
        "HOUSETRAINED"          : a["ISHOUSETRAINEDNAME"],
        "DISPLAYCATSIFGOODWITH" : asm3.utils.iif(a["ISGOODWITHCATS"] == 0, _("Cats", l), ""),
        "DISPLAYDOGSIFGOODWITH" : asm3.utils.iif(a["ISGOODWITHDOGS"] == 0, _("Dogs", l), ""),
        "DISPLAYCHILDRENIFGOODWITH" : asm3.utils.iif(a["ISGOODWITHCHILDREN"] == 0, _("Children", l), ""),
        "DISPLAYCATSIFBADWITH" : asm3.utils.iif(a["ISGOODWITHCATS"] == 1, _("Cats", l), ""),
        "DISPLAYDOGSIFBADWITH" : asm3.utils.iif(a["ISGOODWITHDOGS"] == 1, _("Dogs", l), ""),
        "DISPLAYCHILDRENIFBADWITH" : asm3.utils.iif(a["ISGOODWITHCHILDREN"] == 1, _("Children", l), ""),
        "PICKUPLOCATIONNAME"    : asm3.utils.iif(a["ISPICKUP"] == 1, asm3.utils.nulltostr(a["PICKUPLOCATIONNAME"]), ""),
        "PICKUPADDRESS"         : asm3.utils.iif(a["ISPICKUP"] == 1, asm3.utils.nulltostr(a["PICKUPADDRESS"]), ""),
        "NAMEOFPERSONBROUGHTANIMALIN" : a["BROUGHTINBYOWNERNAME"],
        "ADDRESSOFPERSONBROUGHTANIMALIN" : a["BROUGHTINBYOWNERADDRESS"],
        "TOWNOFPERSONBROUGHTANIMALIN" : a["BROUGHTINBYOWNERTOWN"],
        "COUNTYOFPERSONBROUGHTANIMALIN": a["BROUGHTINBYOWNERCOUNTY"],
        "POSTCODEOFPERSONBROUGHTIN": a["BROUGHTINBYOWNERPOSTCODE"],
        "CITYOFPERSONBROUGHTANIMALIN" : a["BROUGHTINBYOWNERTOWN"],
        "STATEOFPERSONBROUGHTANIMALIN": a["BROUGHTINBYOWNERCOUNTY"],
        "ZIPCODEOFPERSONBROUGHTIN": a["BROUGHTINBYOWNERPOSTCODE"],
        "BROUGHTINBYNAME"     : a["BROUGHTINBYOWNERNAME"],
        "BROUGHTINBYADDRESS"  : a["BROUGHTINBYOWNERADDRESS"],
        "BROUGHTINBYTOWN"     : a["BROUGHTINBYOWNERTOWN"],
        "BROUGHTINBYCOUNTY"   : a["BROUGHTINBYOWNERCOUNTY"],
        "BROUGHTINBYPOSTCODE" : a["BROUGHTINBYOWNERPOSTCODE"],
        "BROUGHTINBYCITY"     : a["BROUGHTINBYOWNERTOWN"],
        "BROUGHTINBYSTATE"    : a["BROUGHTINBYOWNERCOUNTY"],
        "BROUGHTINBYZIPCODE"  : a["BROUGHTINBYOWNERPOSTCODE"],
        "BROUGHTINBYHOMEPHONE" : a["BROUGHTINBYHOMETELEPHONE"],
        "BROUGHTINBYPHONE"    : a["BROUGHTINBYHOMETELEPHONE"],
        "BROUGHTINBYWORKPHONE" : a["BROUGHTINBYWORKTELEPHONE"],
        "BROUGHTINBYMOBILEPHONE" : a["BROUGHTINBYMOBILETELEPHONE"],
        "BROUGHTINBYCELLPHONE" : a["BROUGHTINBYMOBILETELEPHONE"],
        "BROUGHTINBYEMAIL"    : a["BROUGHTINBYEMAILADDRESS"],
        "BROUGHTINBYJURISDICTION" : a["BROUGHTINBYJURISDICTION"],
        "BONDEDANIMAL1NAME"     : a["BONDEDANIMAL1NAME"],
        "BONDEDANIMAL1CODE"     : a["BONDEDANIMAL1CODE"],
        "BONDEDANIMAL2NAME"     : a["BONDEDANIMAL2NAME"],
        "BONDEDANIMAL2CODE"     : a["BONDEDANIMAL2CODE"],
        "NAMEOFOWNERSVET"       : a["OWNERSVETNAME"],
        "NAMEOFCURRENTVET"      : a["CURRENTVETNAME"],
        "HASSPECIALNEEDS"       : a["HASSPECIALNEEDSNAME"],
        "NEUTERED"              : a["NEUTEREDNAME"],
        "FIXED"                 : a["NEUTEREDNAME"],
        "ALTERED"               : a["NEUTEREDNAME"],
        "NEUTEREDDATE"          : python2display(l, a["NEUTEREDDATE"]),
        "FIXEDDATE"             : python2display(l, a["NEUTEREDDATE"]),
        "ALTEREDDATE"           : python2display(l, a["NEUTEREDDATE"]),
        "NEUTERINGVETNAME"      : a["NEUTERINGVETNAME"],
        "NEUTERINGVETADDRESS"   : a["NEUTERINGVETADDRESS"],
        "NEUTERINGVETTOWN"      : a["NEUTERINGVETTOWN"],
        "NEUTERINGVETCOUNTY"    : a["NEUTERINGVETCOUNTY"],
        "NEUTERINGVETPOSTCODE"  : a["NEUTERINGVETPOSTCODE"],
        "NEUTERINGVETCITY"      : a["NEUTERINGVETTOWN"],
        "NEUTERINGVETSTATE"     : a["NEUTERINGVETCOUNTY"],
        "NEUTERINGVETZIPCODE"   : a["NEUTERINGVETPOSTCODE"],
        "NEUTERINGVETPHONE"     : a["NEUTERINGVETWORKTELEPHONE"],
        "NEUTERINGVETEMAIL"     : a["NEUTERINGVETEMAILADDRESS"],
        "NEUTERINGVETLICENSE"   : a["NEUTERINGVETLICENCENUMBER"],
        "NEUTERINGVETLICENCE"   : a["NEUTERINGVETLICENCENUMBER"],
        "COORDINATORNAME"       : a["ADOPTIONCOORDINATORNAME"],
        "COORDINATORHOMEPHONE"  : a["ADOPTIONCOORDINATORHOMETELEPHONE"],
        "COORDINATORWORKPHONE"  : a["ADOPTIONCOORDINATORWORKTELEPHONE"],
        "COORDINATORMOBILEPHONE" : a["ADOPTIONCOORDINATORMOBILETELEPHONE"],
        "COORDINATORCELLPHONE"  : a["ADOPTIONCOORDINATORMOBILETELEPHONE"],
        "COORDINATOREMAIL"      : a["ADOPTIONCOORDINATOREMAILADDRESS"],
        "ORIGINALOWNERNAME"     : a["ORIGINALOWNERNAME"],
        "ORIGINALOWNERADDRESS"  : a["ORIGINALOWNERADDRESS"],
        "ORIGINALOWNERTOWN"     : a["ORIGINALOWNERTOWN"],
        "ORIGINALOWNERCOUNTY"   : a["ORIGINALOWNERCOUNTY"],
        "ORIGINALOWNERPOSTCODE" : a["ORIGINALOWNERPOSTCODE"],
        "ORIGINALOWNERCITY"     : a["ORIGINALOWNERTOWN"],
        "ORIGINALOWNERSTATE"    : a["ORIGINALOWNERCOUNTY"],
        "ORIGINALOWNERZIPCODE"  : a["ORIGINALOWNERPOSTCODE"],
        "ORIGINALOWNERHOMEPHONE" : a["ORIGINALOWNERHOMETELEPHONE"],
        "ORIGINALOWNERPHONE"    : a["ORIGINALOWNERHOMETELEPHONE"],
        "ORIGINALOWNERWORKPHONE" : a["ORIGINALOWNERWORKTELEPHONE"],
        "ORIGINALOWNERMOBILEPHONE" : a["ORIGINALOWNERMOBILETELEPHONE"],
        "ORIGINALOWNERCELLPHONE" : a["ORIGINALOWNERMOBILETELEPHONE"],
        "ORIGINALOWNEREMAIL"    : a["ORIGINALOWNEREMAILADDRESS"],
        "ORIGINALOWNERJURISDICTION" : a["ORIGINALOWNERJURISDICTION"],
        "CURRENTOWNERNAME"     : a["CURRENTOWNERNAME"],
        "CURRENTOWNERADDRESS"  : a["CURRENTOWNERADDRESS"],
        "CURRENTOWNERTOWN"     : a["CURRENTOWNERTOWN"],
        "CURRENTOWNERCOUNTY"   : a["CURRENTOWNERCOUNTY"],
        "CURRENTOWNERPOSTCODE" : a["CURRENTOWNERPOSTCODE"],
        "CURRENTOWNERCITY"     : a["CURRENTOWNERTOWN"],
        "CURRENTOWNERSTATE"    : a["CURRENTOWNERCOUNTY"],
        "CURRENTOWNERZIPCODE"  : a["CURRENTOWNERPOSTCODE"],
        "CURRENTOWNERHOMEPHONE" : a["CURRENTOWNERHOMETELEPHONE"],
        "CURRENTOWNERPHONE"    : a["CURRENTOWNERHOMETELEPHONE"],
        "CURRENTOWNERWORKPHONE" : a["CURRENTOWNERWORKTELEPHONE"],
        "CURRENTOWNERMOBILEPHONE" : a["CURRENTOWNERMOBILETELEPHONE"],
        "CURRENTOWNERCELLPHONE" : a["CURRENTOWNERMOBILETELEPHONE"],
        "CURRENTOWNEREMAIL"     : a["CURRENTOWNEREMAILADDRESS"],
        "CURRENTOWNERJURISDICTION" : a["CURRENTOWNERJURISDICTION"],
        "CURRENTVETNAME"        : a["CURRENTVETNAME"],
        "CURRENTVETADDRESS"     : a["CURRENTVETADDRESS"],
        "CURRENTVETTOWN"        : a["CURRENTVETTOWN"],
        "CURRENTVETCOUNTY"      : a["CURRENTVETCOUNTY"],
        "CURRENTVETPOSTCODE"    : a["CURRENTVETPOSTCODE"],
        "CURRENTVETCITY"        : a["CURRENTVETTOWN"],
        "CURRENTVETSTATE"       : a["CURRENTVETCOUNTY"],
        "CURRENTVETZIPCODE"     : a["CURRENTVETPOSTCODE"],
        "CURRENTVETPHONE"       : a["CURRENTVETWORKTELEPHONE"],
        "CURRENTVETEMAIL"       : a["CURRENTVETEMAILADDRESS"],
        "CURRENTVETLICENSE"     : a["CURRENTVETLICENCENUMBER"],
        "CURRENTVETLICENCE"     : a["CURRENTVETLICENCENUMBER"],
        "OWNERSVETNAME"         : a["OWNERSVETNAME"],
        "OWNERSVETADDRESS"      : a["OWNERSVETADDRESS"],
        "OWNERSVETTOWN"         : a["OWNERSVETTOWN"],
        "OWNERSVETCOUNTY"       : a["OWNERSVETCOUNTY"],
        "OWNERSVETPOSTCODE"     : a["OWNERSVETPOSTCODE"],
        "OWNERSVETCITY"         : a["OWNERSVETTOWN"],
        "OWNERSVETSTATE"        : a["OWNERSVETCOUNTY"],
        "OWNERSVETZIPCODE"      : a["OWNERSVETPOSTCODE"],
        "OWNERSVETPHONE"        : a["OWNERSVETWORKTELEPHONE"],
        "OWNERSVETEMAIL"        : a["OWNERSVETEMAILADDRESS"],
        "OWNERSVETLICENSE"      : a["OWNERSVETLICENCENUMBER"],
        "OWNERSVETLICENCE"      : a["OWNERSVETLICENCENUMBER"],
        "RESERVEDOWNERNAME"     : a["RESERVEDOWNERNAME"],
        "RESERVEDOWNERADDRESS"  : a["RESERVEDOWNERADDRESS"],
        "RESERVEDOWNERTOWN"     : a["RESERVEDOWNERTOWN"],
        "RESERVEDOWNERCOUNTY"   : a["RESERVEDOWNERCOUNTY"],
        "RESERVEDOWNERPOSTCODE" : a["RESERVEDOWNERPOSTCODE"],
        "RESERVEDOWNERCITY"     : a["RESERVEDOWNERTOWN"],
        "RESERVEDOWNERSTATE"    : a["RESERVEDOWNERCOUNTY"],
        "RESERVEDOWNERZIPCODE"  : a["RESERVEDOWNERPOSTCODE"],
        "RESERVEDOWNERHOMEPHONE" : a["RESERVEDOWNERHOMETELEPHONE"],
        "RESERVEDOWNERPHONE"    : a["RESERVEDOWNERHOMETELEPHONE"],
        "RESERVEDOWNERWORKPHONE" : a["RESERVEDOWNERWORKTELEPHONE"],
        "RESERVEDOWNERMOBILEPHONE" : a["RESERVEDOWNERMOBILETELEPHONE"],
        "RESERVEDOWNERCELLPHONE" : a["RESERVEDOWNERMOBILETELEPHONE"],
        "RESERVEDOWNEREMAIL"    : a["RESERVEDOWNEREMAILADDRESS"],
        "RESERVEDOWNERJURISDICTION" : a["RESERVEDOWNERJURISDICTION"],
        "ENTRYCATEGORY"         : a["ENTRYREASONNAME"],
        "MOSTRECENTENTRYCATEGORY" : a["ENTRYREASONNAME"],
        "REASONFORENTRY"        : a["REASONFORENTRY"],
        "REASONFORENTRYBR"      : br(a["REASONFORENTRY"]),
        "REASONNOTBROUGHTBYOWNER" : a["REASONNO"],
        "SEX"                   : a["SEXNAME"],
        "SIZE"                  : a["SIZENAME"],
        "WEIGHT"                : asm3.utils.nulltostr(a["WEIGHT"]),
        "DISPLAYWEIGHT"         : weight_display(dbo, a["WEIGHT"]),
        "SPECIESNAME"           : a["SPECIESNAME"],
        "ANIMALFLAGS"           : asm3.utils.nulltostr(a["ADDITIONALFLAGS"]).replace("|", ", "),
        "ANIMALCOMMENTS"        : a["ANIMALCOMMENTS"],
        "ANIMALCOMMENTSBR"      : br(a["ANIMALCOMMENTS"]),
        "DESCRIPTION"           : a["ANIMALCOMMENTS"],
        "DESCRIPTIONBR"         : br(a["ANIMALCOMMENTS"]),
        "SHELTERCODE"           : a["SHELTERCODE"],
        "AGE"                   : animalage,
        "ACCEPTANCENUMBER"      : a["ACCEPTANCENUMBER"],
        "LITTERID"              : a["ACCEPTANCENUMBER"],
        "DECEASEDDATE"          : python2display(l, a["DECEASEDDATE"]),
        "DECEASEDNOTES"         : a["PTSREASON"],
        "DECEASEDCATEGORY"      : a["PTSREASONNAME"],
        "SHORTSHELTERCODE"      : a["SHORTCODE"],
        "MOSTRECENTENTRY"       : python2display(l, a["MOSTRECENTENTRYDATE"]),
        "MOSTRECENTENTRYDATE"   : python2display(l, a["MOSTRECENTENTRYDATE"]),
        "TIMEONSHELTER"         : timeonshelter,
        "WEBMEDIAFILENAME"      : a["WEBSITEMEDIANAME"],
        "WEBSITEIMAGECOUNT"     : a["WEBSITEIMAGECOUNT"],
        "WEBSITEMEDIANAME"      : a["WEBSITEMEDIANAME"],
        "WEBSITEVIDEOURL"       : a["WEBSITEVIDEOURL"],
        "WEBSITEVIDEONOTES"     : a["WEBSITEVIDEONOTES"],
        "WEBMEDIANOTES"         : a["WEBSITEMEDIANOTES"],
        "WEBSITEMEDIANOTES"     : a["WEBSITEMEDIANOTES"],
        "DOCUMENTIMGSRC"        : asm3.html.doc_img_src(dbo, a),
        "DOCUMENTIMGLINK"       : "<img height=\"200\" src=\"" + asm3.html.doc_img_src(dbo, a) + "\" >",
        "DOCUMENTIMGLINK200"    : "<img height=\"200\" src=\"" + asm3.html.doc_img_src(dbo, a) + "\" >",
        "DOCUMENTIMGLINK300"    : "<img height=\"300\" src=\"" + asm3.html.doc_img_src(dbo, a) + "\" >",
        "DOCUMENTIMGLINK400"    : "<img height=\"400\" src=\"" + asm3.html.doc_img_src(dbo, a) + "\" >",
        "DOCUMENTIMGLINK500"    : "<img height=\"500\" src=\"" + asm3.html.doc_img_src(dbo, a) + "\" >",
        "DOCUMENTIMGTHUMBSRC"   : asm3.html.thumbnail_img_src(dbo, a, "animalthumb"),
        "DOCUMENTIMGTHUMBLINK"  : "<img src=\"" + asm3.html.thumbnail_img_src(dbo, a, "animalthumb") + "\" />",
        "DOCUMENTQRLINK"        : "<img src=\"%s\" />" % asm3.html.qr_animal_img_src(a.ID),
        "DOCUMENTQRLINK200"     : "<img src=\"%s\" />" % asm3.html.qr_animal_img_src(a.ID, "200x200"),
        "DOCUMENTQRLINK150"     : "<img src=\"%s\" />" % asm3.html.qr_animal_img_src(a.ID, "150x150"),
        "DOCUMENTQRLINK100"     : "<img src=\"%s\" />" % asm3.html.qr_animal_img_src(a.ID, "100x100"),
        "DOCUMENTQRLINK50"      : "<img src=\"%s\" />" % asm3.html.qr_animal_img_src(a.ID, "50x50"),
        "ADOPTIONSTATUS"        : asm3.publishers.base.get_adoption_status(dbo, a),
        "ANIMALISADOPTABLE"     : asm3.utils.iif(asm3.publishers.base.is_animal_adoptable(dbo, a), _("Yes", l), _("No", l)),
        "ANIMALONSHELTER"       : yes_no(l, a["ARCHIVED"] == 0),
        "ANIMALONFOSTER"        : yes_no(l, a["ACTIVEMOVEMENTTYPE"] == asm3.movement.FOSTER),
        "ANIMALPERMANENTFOSTER" : yes_no(l, a["HASPERMANENTFOSTER"] == 1),
        "ANIMALATRETAILER"      : yes_no(l, a["ACTIVEMOVEMENTTYPE"] == asm3.movement.RETAILER),
        "ANIMALISRESERVED"      : yes_no(l, a["HASACTIVERESERVE"] == 1),
        "ADOPTIONID"            : a["ACTIVEMOVEMENTADOPTIONNUMBER"],
        "OUTCOMEDATE"           : asm3.utils.iif(a["DECEASEDDATE"] is None, python2display(l, a["ACTIVEMOVEMENTDATE"]), python2display(l, a["DECEASEDDATE"])),
        "OUTCOMETYPE"           : asm3.utils.iif(a["ARCHIVED"] == 1, a["DISPLAYLOCATIONNAME"], "")
    }

    # Set original owner to be current owner on non-shelter animals
    if a["NONSHELTERANIMAL"] == 1 and a["ORIGINALOWNERNAME"] is not None and a["ORIGINALOWNERNAME"] != "":
        tags["CURRENTOWNERNAME"] = a["ORIGINALOWNERNAME"]
        tags["CURRENTOWNERADDRESS"] = a["ORIGINALOWNERADDRESS"]
        tags["CURRENTOWNERTOWN"] = a["ORIGINALOWNERTOWN"]
        tags["CURRENTOWNERCOUNTY"] = a["ORIGINALOWNERCOUNTY"]
        tags["CURRENTOWNERPOSTCODE"] = a["ORIGINALOWNERPOSTCODE"]
        tags["CURRENTOWNERCITY"] = a["ORIGINALOWNERTOWN"]
        tags["CURRENTOWNERSTATE"] = a["ORIGINALOWNERCOUNTY"]
        tags["CURRENTOWNERZIPCODE"] = a["ORIGINALOWNERPOSTCODE"]
        tags["CURRENTOWNERHOMEPHONE"] = a["ORIGINALOWNERHOMETELEPHONE"]
        tags["CURRENTOWNERPHONE"] = a["ORIGINALOWNERHOMETELEPHONE"]
        tags["CURRENTOWNERWORKPHONE"] = a["ORIGINALOWNERWORKTELEPHONE"]
        tags["CURRENTOWNERMOBILEPHONE"] = a["ORIGINALOWNERMOBILETELEPHONE"]
        tags["CURRENTOWNERCELLPHONE"] = a["ORIGINALOWNERMOBILETELEPHONE"]
        tags["CURRENTOWNEREMAIL"] = a["ORIGINALOWNEREMAILADDRESS"]

    # If the animal doesn't have a current owner, but does have an open
    # movement with a future date on it, look up the owner and use that 
    # instead so that we can still generate paperwork for future adoptions.
    if includeFutureOwner and a["CURRENTOWNERID"] is None or a["CURRENTOWNERID"] == 0:
        latest = asm3.movement.get_animal_movements(dbo, a["ID"])
        if len(latest) > 0:
            latest = latest[0]
            if latest["MOVEMENTDATE"] is not None and latest["RETURNDATE"] is None:
                p = asm3.person.get_person(dbo, latest["OWNERID"])
                a["CURRENTOWNERID"] = latest["OWNERID"]
                if p is not None:
                    tags["CURRENTOWNERNAME"] = p["OWNERNAME"]
                    tags["CURRENTOWNERADDRESS"] = p["OWNERADDRESS"]
                    tags["CURRENTOWNERTOWN"] = p["OWNERTOWN"]
                    tags["CURRENTOWNERCOUNTY"] = p["OWNERCOUNTY"]
                    tags["CURRENTOWNERPOSTCODE"] = p["OWNERPOSTCODE"]
                    tags["CURRENTOWNERCITY"] = p["OWNERTOWN"]
                    tags["CURRENTOWNERSTATE"] = p["OWNERCOUNTY"]
                    tags["CURRENTOWNERZIPCODE"] = p["OWNERPOSTCODE"]
                    tags["CURRENTOWNERHOMEPHONE"] = p["HOMETELEPHONE"]
                    tags["CURRENTOWNERPHONE"] = p["HOMETELEPHONE"]
                    tags["CURRENTOWNERWORKPHONE"] = p["WORKTELEPHONE"]
                    tags["CURRENTOWNERMOBILEPHONE"] = p["MOBILETELEPHONE"]
                    tags["CURRENTOWNERCELLPHONE"] = p["MOBILETELEPHONE"]
                    tags["CURRENTOWNEREMAIL"] = p["EMAILADDRESS"]

            # If the latest movement is an adoption return, update the MOSTRECENTENTRYCATEGORY field
            if latest["MOVEMENTTYPE"] == 1 and latest["RETURNDATE"] is not None:
                tags["MOSTRECENTENTRYCATEGORY"] = latest["RETURNEDREASONNAME"]

    # Additional fields
    if includeAdditional:
        tags.update(additional_field_tags(dbo, asm3.additional.get_additional_fields(dbo, a["ID"], "animal")))
        if a["ORIGINALOWNERID"] and a["ORIGINALOWNERID"] > 0:
            tags.update(additional_field_tags(dbo, asm3.additional.get_additional_fields(dbo, a["ORIGINALOWNERID"], "person"), "ORIGINALOWNER"))
        if a["BROUGHTINBYOWNERID"] and a["BROUGHTINBYOWNERID"] > 0:
            tags.update(additional_field_tags(dbo, asm3.additional.get_additional_fields(dbo, a["BROUGHTINBYOWNERID"], "person"), "BROUGHTINBY"))
        if a["CURRENTOWNERID"] and a["CURRENTOWNERID"] > 0:
            tags.update(additional_field_tags(dbo, asm3.additional.get_additional_fields(dbo, a["CURRENTOWNERID"], "person"), "CURRENTOWNER"))

    # Is vaccinated indicator
    if includeIsVaccinated:    
        tags["ANIMALISVACCINATED"] = asm3.utils.iif(asm3.medical.get_vaccinated(dbo, a["ID"]), _("Yes", l), _("No", l))

    if includeMedical:
        iic = asm3.configuration.include_incomplete_medical_doc(dbo)
        # Vaccinations
        d = {
            "VACCINATIONNAME":          "VACCINATIONTYPE",
            "VACCINATIONREQUIRED":      "d:DATEREQUIRED",
            "VACCINATIONGIVEN":         "d:DATEOFVACCINATION",
            "VACCINATIONEXPIRES":       "d:DATEEXPIRES",
            "VACCINATIONBATCH":         "BATCHNUMBER",
            "VACCINATIONMANUFACTURER":  "MANUFACTURER",
            "VACCINATIONCOST":          "c:COST",
            "VACCINATIONCOMMENTS":      "COMMENTS",
            "VACCINATIONDESCRIPTION":   "VACCINATIONDESCRIPTION",
            "VACCINATIONADMINISTERINGVETNAME":      "ADMINISTERINGVETNAME",
            "VACCINATIONADMINISTERINGVETLICENCE":   "ADMINISTERINGVETLICENCE",
            "VACCINATIONADMINISTERINGVETLICENSE":   "ADMINISTERINGVETLICENCE",
            "VACCINATIONADMINISTERINGVETADDRESS":   "ADMINISTERINGVETADDRESS",
            "VACCINATIONADMINISTERINGVETTOWN":      "ADMINISTERINGVETTOWN",
            "VACCINATIONADMINISTERINGVETCITY":      "ADMINISTERINGVETTOWN",
            "VACCINATIONADMINISTERINGVETCOUNTY":    "ADMINISTERINGVETCOUNTY",
            "VACCINATIONADMINISTERINGVETSTATE":     "ADMINISTERINGVETCOUNTY",
            "VACCINATIONADMINISTERINGVETPOSTCODE":  "ADMINISTERINGVETPOSTCODE",
            "VACCINATIONADMINISTERINGVETZIPCODE":   "ADMINISTERINGVETPOSTCODE",
            "VACCINATIONADMINISTERINGVETEMAIL":     "ADMINISTERINGVETEMAIL"
        }
        vaccinations = asm3.medical.get_vaccinations(dbo, a["ID"], not iic)
        tags.update(table_tags(dbo, d, vaccinations, "VACCINATIONTYPE", "DATEREQUIRED", "DATEOFVACCINATION"))
        tags["ANIMALVACCINATIONS"] = html_table(l, vaccinations, (
            ( "VACCINATIONTYPE", _("Type", l) ),
            ( "DATEREQUIRED", _("Due", l)),
            ( "DATEOFVACCINATION", _("Given", l)),
            ( "MANUFACTURER", _("Manufacturer", l)),
            ( "COMMENTS", _("Comments", l)) 
        ))

        # Tests
        d = {
            "TESTNAME":                 "TESTNAME",
            "TESTRESULT":               "RESULTNAME",
            "TESTREQUIRED":             "d:DATEREQUIRED",
            "TESTGIVEN":                "d:DATEOFTEST",
            "TESTCOST":                 "c:COST",
            "TESTCOMMENTS":             "COMMENTS",
            "TESTDESCRIPTION":          "TESTDESCRIPTION",
            "TESTADMINISTERINGVETNAME":      "ADMINISTERINGVETNAME",
            "TESTADMINISTERINGVETLICENCE":   "ADMINISTERINGVETLICENCE",
            "TESTADMINISTERINGVETLICENSE":   "ADMINISTERINGVETLICENCE",
            "TESTADMINISTERINGVETADDRESS":   "ADMINISTERINGVETADDRESS",
            "TESTADMINISTERINGVETTOWN":      "ADMINISTERINGVETTOWN",
            "TESTADMINISTERINGVETCITY":      "ADMINISTERINGVETTOWN",
            "TESTADMINISTERINGVETCOUNTY":    "ADMINISTERINGVETCOUNTY",
            "TESTADMINISTERINGVETSTATE":     "ADMINISTERINGVETCOUNTY",
            "TESTADMINISTERINGVETPOSTCODE":  "ADMINISTERINGVETPOSTCODE",
            "TESTADMINISTERINGVETZIPCODE":   "ADMINISTERINGVETPOSTCODE",
            "TESTADMINISTERINGVETEMAIL":     "ADMINISTERINGVETEMAIL"
        }
        tests = asm3.medical.get_tests(dbo, a["ID"], not iic)
        tags.update(table_tags(dbo, d, tests, "TESTNAME", "DATEREQUIRED", "DATEOFTEST"))
        tags["ANIMALTESTS"] = html_table(l, tests, (
            ( "TESTNAME", _("Type", l) ),
            ( "DATEREQUIRED", _("Required", l)),
            ( "DATEOFTEST", _("Performed", l)),
            ( "RESULTNAME", _("Result", l)),
            ( "COMMENTS", _("Comments", l)) 
        ))

        # Medical
        d = {
            "MEDICALNAME":              "TREATMENTNAME",
            "MEDICALCOMMENTS":          "COMMENTS",
            "MEDICALFREQUENCY":         "NAMEDFREQUENCY",
            "MEDICALNUMBEROFTREATMENTS": "NAMEDNUMBEROFTREATMENTS",
            "MEDICALSTATUS":            "NAMEDSTATUS",
            "MEDICALDOSAGE":            "DOSAGE",
            "MEDICALSTARTDATE":         "d:STARTDATE",
            "MEDICALTREATMENTSGIVEN":   "TREATMENTSGIVEN",
            "MEDICALTREATMENTSREMAINING": "TREATMENTSREMAINING",
            "MEDICALNEXTTREATMENTDUE":  "d:NEXTTREATMENTDUE",
            "MEDICALLASTTREATMENTGIVEN": "d:LASTTREATMENTGIVEN",
            "MEDICALLASTTREATMENTCOMMENTS": "LASTTREATMENTCOMMENTS",
            "MEDICALCOST":              "c:COST"
        }
        medicals = asm3.medical.get_regimens(dbo, a["ID"], not iic)
        tags.update(table_tags(dbo, d, medicals, "TREATMENTNAME", "NEXTTREATMENTDUE", "LASTTREATMENTGIVEN"))
        tags["ANIMALMEDICALS"] = html_table(l, medicals, (
            ( "TREATMENTNAME", _("Treatment", l) ),
            ( "DOSAGE", _("Dosage", l) ),
            ( "LASTTREATMENTGIVEN", _("Given", l)),
            ( "NEXTTREATMENTDUE", _("Due", l)),
            ( "COMMENTS", _("Comments", l)) 
        ))

    # Diet
    if includeDiet:
        d = {
            "DIETNAME":                 "DIETNAME",
            "DIETDESCRIPTION":          "DIETDESCRIPTION",
            "DIETDATESTARTED":          "d:DATESTARTED",
            "DIETCOMMENTS":             "COMMENTS"
        }
        tags.update(table_tags(dbo, d, asm3.animal.get_diets(dbo, a["ID"]), "DIETNAME", "DATESTARTED", "DATESTARTED"))

    # Donations
    if includeDonations:
        d = {
            "RECEIPTNUM":               "RECEIPTNUMBER",
            "DONATIONTYPE":             "DONATIONNAME",
            "DONATIONPAYMENTTYPE":      "PAYMENTNAME",
            "DONATIONDATE":             "d:DATE",
            "DONATIONDATEDUE":          "d:DATEDUE",
            "DONATIONAMOUNT":           "c:DONATION",
            "DONATIONCOMMENTS":         "COMMENTS",
            "DONATIONGIFTAID":          "y:ISGIFTAID",
            "PAYMENTTYPE":              "DONATIONNAME",
            "PAYMENTMETHOD":            "PAYMENTNAME",
            "PAYMENTDATE":              "d:DATE",
            "PAYMENTDATEDUE":           "d:DATEDUE",
            "PAYMENTAMOUNT":            "c:DONATION",
            "PAYMENTCOMMENTS":          "COMMENTS",
            "PAYMENTGIFTAID":           "y:ISGIFTAID",
            "PAYMENTVAT":               "y:ISVAT",
            "PAYMENTTAX":               "y:ISVAT",
            "PAYMENTVATRATE":           "f:VATRATE",
            "PAYMENTTAXRATE":           "f:VATRATE",
            "PAYMENTVATAMOUNT":         "c:VATAMOUNT",
            "PAYMENTTAXAMOUNT":         "c:VATAMOUNT"
        }
        tags.update(table_tags(dbo, d, asm3.financial.get_animal_donations(dbo, a["ID"]), "DONATIONNAME", "DATEDUE", "DATE"))

    # Transport
    if includeTransport:
        d = {
            "TRANSPORTTYPE":            "TRANSPORTTYPENAME",
            "TRANSPORTDRIVERNAME":      "DRIVEROWNERNAME", 
            "TRANSPORTPICKUPDATETIME":  "d:PICKUPDATETIME",
            "TRANSPORTPICKUPNAME":      "PICKUPOWNERNAME", 
            "TRANSPORTPICKUPADDRESS":   "PICKUPADDRESS",
            "TRANSPORTPICKUPTOWN":      "PICKUPTOWN",
            "TRANSPORTPICKUPCITY":      "PICKUPTOWN",
            "TRANSPORTPICKUPCOUNTY":    "PICKUPCOUNTY",
            "TRANSPORTPICKUPSTATE":     "PICKUPCOUNTY",
            "TRANSPORTPICKUPZIPCODE":   "PICKUPPOSTCODE",
            "TRANSPORTPICKUPPOSTCODE":  "PICKUPPOSTCODE",
            "TRANSPORTPICKUPCOUNTRY":   "PICKUPCOUNTRY",
            "TRANSPORTPICKUPEMAIL":     "PICKUPEMAILADDRESS",
            "TRANSPORTPICKUPHOMEPHONE": "PICKUPHOMETELEPHONE",
            "TRANSPORTPICKUPWORKPHONE": "PICKUPWORKTELEPHONE",
            "TRANSPORTPICKUPMOBILEPHONE": "PICKUPMOBILETELEPHONE",
            "TRANSPORTPICKUPCELLPHONE": "PICKUPMOBILETELEPHONE",
            "TRANSPORTDROPOFFNAME":     "DROPOFFOWNERNAME", 
            "TRANSPORTDROPOFFDATETIME": "d:DROPOFFDATETIME",
            "TRANSPORTDROPOFFADDRESS":  "DROPOFFADDRESS",
            "TRANSPORTDROPOFFTOWN":     "DROPOFFTOWN",
            "TRANSPORTDROPOFFCITY":     "DROPOFFTOWN",
            "TRANSPORTDROPOFFCOUNTY":   "DROPOFFCOUNTY",
            "TRANSPORTDROPOFFSTATE":    "DROPOFFCOUNTY",
            "TRANSPORTDROPOFFZIPCODE":  "DROPOFFPOSTCODE",
            "TRANSPORTDROPOFFPOSTCODE": "DROPOFFPOSTCODE",
            "TRANSPORTDROPOFFCOUNTRY":  "DROPOFFCOUNTRY",
            "TRANSPORTDROPOFFEMAIL":    "DROPOFFEMAILADDRESS",
            "TRANSPORTDROPOFFHOMEPHONE": "DROPOFFHOMETELEPHONE",
            "TRANSPORTDROPOFFWORKPHONE": "DROPOFFWORKTELEPHONE",
            "TRANSPORTDROPOFFMOBILEPHONE": "DROPOFFMOBILETELEPHONE",
            "TRANSPORTDROPOFFCELLPHONE": "DROPOFFMOBILETELEPHONE",
            "TRANSPORTMILES":           "MILES",
            "TRANSPORTCOST":            "c:COST",
            "TRANSPORTCOSTPAIDDATE":    "d:COSTPAIDDATE",
            "TRANSPORTCOMMENTS":        "COMMENTS"
        }
        tags.update(table_tags(dbo, d, asm3.movement.get_animal_transports(dbo, a["ID"]), "TRANSPORTTYPENAME", "PICKUPDATETIME", "DROPOFFDATETIME"))

    # Costs
    if includeCosts:
        d = {
            "COSTTYPE":                 "COSTTYPENAME",
            "COSTDATE":                 "d:COSTDATE",
            "COSTDATEPAID":             "d:COSTPAIDDATE",
            "COSTAMOUNT":               "c:COSTAMOUNT",
            "COSTDESCRIPTION":          "DESCRIPTION"
        }
        tags.update(table_tags(dbo, d, asm3.animal.get_costs(dbo, a["ID"]), "COSTTYPENAME", "COSTDATE", "COSTPAIDDATE"))

        # Cost totals
        totalvaccinations = dbo.query_int("SELECT SUM(Cost) FROM animalvaccination WHERE AnimalID = ?", [a["ID"]])
        totaltransports = dbo.query_int("SELECT SUM(Cost) FROM animaltransport WHERE AnimalID = ?", [a["ID"]])
        totaltests = dbo.query_int("SELECT SUM(Cost) FROM animaltest WHERE AnimalID = ?", [a["ID"]])
        totalmedicals = dbo.query_int("SELECT SUM(Cost) FROM animalmedical WHERE AnimalID = ?", [a["ID"]])
        totallines = dbo.query_int("SELECT SUM(CostAmount) FROM animalcost WHERE AnimalID = ?", [a["ID"]])
        totalcosts = totalvaccinations + totaltransports + totaltests + totalmedicals + totallines
        dailyboardingcost = a["DAILYBOARDINGCOST"] or 0
        daysonshelter = a["DAYSONSHELTER"] or 0
        costtags = {
            "TOTALVACCINATIONCOSTS": format_currency_no_symbol(l, totalvaccinations),
            "TOTALTRANSPORTCOSTS": format_currency_no_symbol(l, totaltransports),
            "TOTALTESTCOSTS": format_currency_no_symbol(l, totaltests),
            "TOTALMEDICALCOSTS": format_currency_no_symbol(l, totalmedicals),
            "TOTALLINECOSTS": format_currency_no_symbol(l, totallines),
            "DAILYBOARDINGCOST": format_currency_no_symbol(l, dailyboardingcost),
            "CURRENTBOARDINGCOST": format_currency_no_symbol(l, dailyboardingcost * daysonshelter),
            "TOTALCOSTS": format_currency_no_symbol(l, dailyboardingcost * daysonshelter + totalcosts)
        }
        tags = append_tags(tags, costtags)

    if includeLogs:
        # Logs
        d = {
            "LOGNAME":                  "LOGTYPENAME",
            "LOGDATE":                  "d:DATE",
            "LOGTIME":                  "t:DATE",
            "LOGCOMMENTS":              "COMMENTS",
            "LOGCREATEDBY":             "CREATEDBY"
        }
        logs = asm3.log.get_logs(dbo, asm3.log.ANIMAL, a["ID"], 0, asm3.log.ASCENDING)
        tags.update(table_tags(dbo, d, logs, "LOGTYPENAME", "DATE", "DATE"))
        tags["ANIMALLOGS"] = html_table(l, logs, (
            ( "DATE", _("Date", l)),
            ( "LOGTYPENAME", _("Type", l)),
            ( "CREATEDBY", _("By", l)),
            ( "COMMENTS", _("Comments", l))
        ))

    return tags

def animalcontrol_tags(dbo, ac):
    """
    Generates a list of tags from an animalcontrol incident.
    ac: An animalcontrol incident record
    """
    l = dbo.locale
    tags = {
        "INCIDENTNUMBER":       asm3.utils.padleft(ac["ACID"], 6),
        "INCIDENTDATE":         python2display(l, ac["INCIDENTDATETIME"]),
        "INCIDENTTIME":         format_time(ac["INCIDENTDATETIME"]),
        "INCIDENTTYPENAME":     asm3.utils.nulltostr(ac["INCIDENTNAME"]),
        "CALLDATE":             python2display(l, ac["CALLDATETIME"]),
        "CALLTIME":             format_time(ac["CALLDATETIME"]),
        "CALLNOTES":            ac["CALLNOTES"],
        "CALLTAKER":            ac["CALLTAKER"],
        "DISPATCHDATE":         python2display(l, ac["DISPATCHDATETIME"]),
        "DISPATCHTIME":         format_time(ac["DISPATCHDATETIME"]),
        "DISPATCHADDRESS":      ac["DISPATCHADDRESS"],
        "DISPATCHTOWN":         ac["DISPATCHTOWN"],
        "DISPATCHCITY":         ac["DISPATCHTOWN"],
        "DISPATCHCOUNTY":       ac["DISPATCHCOUNTY"],
        "DISPATCHSTATE":        ac["DISPATCHCOUNTY"],
        "DISPATCHPOSTCODE":     ac["DISPATCHPOSTCODE"],
        "DISPATCHZIPCODE":      ac["DISPATCHPOSTCODE"],
        "DISPATCHEDACO":        ac["DISPATCHEDACO"],
        "PICKUPLOCATIONNAME":   asm3.utils.nulltostr(ac["LOCATIONNAME"]),
        "RESPONDEDDATE":        python2display(l, ac["RESPONDEDDATETIME"]),
        "RESPONDEDTIME":        format_time(ac["RESPONDEDDATETIME"]),
        "FOLLOWUPDATE":         python2display(l, ac["FOLLOWUPDATETIME"]),
        "FOLLOWUPTIME":         format_time(ac["FOLLOWUPDATETIME"]),
        "FOLLOWUPDATE2":         python2display(l, ac["FOLLOWUPDATETIME2"]),
        "FOLLOWUPTIME2":         format_time(ac["FOLLOWUPDATETIME2"]),
        "FOLLOWUPDATE3":         python2display(l, ac["FOLLOWUPDATETIME3"]),
        "FOLLOWUPTIME3":         format_time(ac["FOLLOWUPDATETIME3"]),
        "COMPLETEDDATE":        python2display(l, ac["COMPLETEDDATE"]),
        "COMPLETEDTYPENAME":    asm3.utils.nulltostr(ac["COMPLETEDNAME"]),
        "ANIMALDESCRIPTION":    ac["ANIMALDESCRIPTION"],
        "SPECIESNAME":          asm3.utils.nulltostr(ac["SPECIESNAME"]),
        "SEX":                  asm3.utils.nulltostr(ac["SEXNAME"]),
        "AGEGROUP":             asm3.utils.nulltostr(ac["AGEGROUP"]),
        "CALLERNAME":           asm3.utils.nulltostr(ac["CALLERNAME"]),
        "CALLERADDRESS":        asm3.utils.nulltostr(ac["CALLERADDRESS"]),
        "CALLERTOWN":           asm3.utils.nulltostr(ac["CALLERTOWN"]),
        "CALLERCITY":           asm3.utils.nulltostr(ac["CALLERTOWN"]),
        "CALLERCOUNTY":         asm3.utils.nulltostr(ac["CALLERCOUNTY"]),
        "CALLERSTATE":          asm3.utils.nulltostr(ac["CALLERCOUNTY"]),
        "CALLERPOSTCODE":       asm3.utils.nulltostr(ac["CALLERPOSTCODE"]),
        "CALLERZIPCODE":        asm3.utils.nulltostr(ac["CALLERPOSTCODE"]),
        "CALLERHOMETELEPHONE":  asm3.utils.nulltostr(ac["CALLERHOMETELEPHONE"]),
        "CALLERWORKTELEPHONE":  asm3.utils.nulltostr(ac["CALLERWORKTELEPHONE"]),
        "CALLERMOBILETELEPHONE": asm3.utils.nulltostr(ac["CALLERMOBILETELEPHONE"]),
        "CALLERCELLTELEPHONE":  asm3.utils.nulltostr(ac["CALLERMOBILETELEPHONE"]),
        "SUSPECTNAME":          asm3.utils.nulltostr(ac["SUSPECTNAME"]),
        "SUSPECTADDRESS":       asm3.utils.nulltostr(ac["SUSPECTADDRESS"]),
        "SUSPECTTOWN":          asm3.utils.nulltostr(ac["SUSPECTTOWN"]),
        "SUSPECTCITY":          asm3.utils.nulltostr(ac["SUSPECTTOWN"]),
        "SUSPECTCOUNTY":        asm3.utils.nulltostr(ac["SUSPECTCOUNTY"]),
        "SUSPECTSTATE":         asm3.utils.nulltostr(ac["SUSPECTCOUNTY"]),
        "SUSPECTPOSTCODE":      asm3.utils.nulltostr(ac["SUSPECTPOSTCODE"]),
        "SUSPECTZIPCODE":       asm3.utils.nulltostr(ac["SUSPECTPOSTCODE"]),
        "SUSPECTHOMETELEPHONE": asm3.utils.nulltostr(ac["SUSPECTHOMETELEPHONE"]),
        "SUSPECTWORKTELEPHONE": asm3.utils.nulltostr(ac["SUSPECTWORKTELEPHONE"]),
        "SUSPECTMOBILETELEPHONE": asm3.utils.nulltostr(ac["SUSPECTMOBILETELEPHONE"]),
        "SUSPECT1NAME":         asm3.utils.nulltostr(ac["OWNERNAME1"]),
        "SUSPECT2NAME":         asm3.utils.nulltostr(ac["OWNERNAME2"]),
        "SUSPECT3NAME":         asm3.utils.nulltostr(ac["OWNERNAME3"]),
        "VICTIMNAME":           asm3.utils.nulltostr(ac["VICTIMNAME"]),
        "VICTIMADDRESS":        asm3.utils.nulltostr(ac["VICTIMADDRESS"]),
        "VICTIMTOWN":           asm3.utils.nulltostr(ac["VICTIMTOWN"]),
        "VICTIMCITY":           asm3.utils.nulltostr(ac["VICTIMTOWN"]),
        "VICTIMCOUNTY":         asm3.utils.nulltostr(ac["VICTIMCOUNTY"]),
        "VICTIMSTATE":          asm3.utils.nulltostr(ac["VICTIMCOUNTY"]),
        "VICTIMPOSTCODE":       asm3.utils.nulltostr(ac["VICTIMPOSTCODE"]),
        "VICTIMHOMETELEPHONE":  asm3.utils.nulltostr(ac["VICTIMHOMETELEPHONE"]),
        "VICTIMWORKTELEPHONE":  asm3.utils.nulltostr(ac["VICTIMWORKTELEPHONE"]),
        "VICTIMMOBILETELEPHONE":  asm3.utils.nulltostr(ac["VICTIMMOBILETELEPHONE"]),
        "VICTIMCELLTELEPHONE":  asm3.utils.nulltostr(ac["VICTIMMOBILETELEPHONE"]),
        "DOCUMENTIMGSRC"        : asm3.html.doc_img_src(dbo, ac),
        "DOCUMENTIMGLINK"       : "<img height=\"200\" src=\"" + asm3.html.doc_img_src(dbo, ac) + "\" >",
        "DOCUMENTIMGLINK200"    : "<img height=\"200\" src=\"" + asm3.html.doc_img_src(dbo, ac) + "\" >",
        "DOCUMENTIMGLINK300"    : "<img height=\"300\" src=\"" + asm3.html.doc_img_src(dbo, ac) + "\" >",
        "DOCUMENTIMGLINK400"    : "<img height=\"400\" src=\"" + asm3.html.doc_img_src(dbo, ac) + "\" >",
        "DOCUMENTIMGLINK500"    : "<img height=\"500\" src=\"" + asm3.html.doc_img_src(dbo, ac) + "\" >"
    }

    # Linked animals
    d = {
        "ANIMALNAME":           "ANIMALNAME",
        "SHELTERCODE":          "SHELTERCODE",
        "SHORTCODE":            "SHORTCODE",
        "AGEGROUP":             "AGEGROUP",
        "ANIMALTYPENAME":       "ANIMALTYPENAME",
        "SPECIESNAME":          "SPECIESNAME",
        "DATEBROUGHTIN":        "d:DATEBROUGHTIN",
        "DECEASEDDATE":         "d:DECEASEDDATE"
    }
    tags.update(table_tags(dbo, d, asm3.animalcontrol.get_animalcontrol_animals(dbo, ac["ID"]), "SPECIESNAME", "DATEBROUGHTIN", "DATEBROUGHTIN"))

    # Additional fields
    tags.update(additional_field_tags(dbo, asm3.additional.get_additional_fields(dbo, ac["ID"], "incident")))

    # Citations
    d = {
        "CITATIONNAME":         "CITATIONNAME",
        "CITATIONDATE":         "d:CITATIONDATE",
        "CITATIONCOMMENTS":     "COMMENTS",
        "FINEAMOUNT":           "c:FINEAMOUNT",
        "FINEDUEDATE":          "d:FINEDUEDATE",
        "FINEPAIDDATE":         "d:FINEPAIDDATE"
    }
    tags.update(table_tags(dbo, d, asm3.financial.get_incident_citations(dbo, ac["ID"]), "CITATIONNAME", "CITATIONDATE", "FINEPAIDDATE"))

    # Logs
    d = {
        "INCIDENTLOGNAME":            "LOGTYPENAME",
        "INCIDENTLOGDATE":            "d:DATE",
        "INCIDENTLOGTIME":            "t:DATE",
        "INCIDENTLOGCOMMENTS":        "COMMENTS",
        "INCIDENTLOGCREATEDBY":       "CREATEDBY"
    }
    tags.update(table_tags(dbo, d, asm3.log.get_logs(dbo, asm3.log.ANIMALCONTROL, ac["ID"], 0, asm3.log.ASCENDING), "LOGTYPENAME", "DATE", "DATE"))

    return tags

def donation_tags(dbo, donations):
    """
    Generates a list of tags from a donation result.
    donations: a list of donation records
    """
    l = dbo.locale
    tags = {}
    totals = { "due": 0, "received": 0, "vat": 0, "total": 0, "taxrate": 0.0 }
    def add_to_tags(i, p): 
        x = { 
            "DONATIONID"+i          : str(p["ID"]),
            "RECEIPTNUM"+i          : p["RECEIPTNUMBER"],
            "CHECKNUM"+i            : p["CHEQUENUMBER"],
            "CHEQUENUM"+i           : p["CHEQUENUMBER"],
            "DONATIONTYPE"+i        : p["DONATIONNAME"],
            "DONATIONPAYMENTTYPE"+i : p["PAYMENTNAME"],
            "DONATIONDATE"+i        : python2display(l, p["DATE"]),
            "DONATIONDATEDUE"+i     : python2display(l, p["DATEDUE"]),
            "DONATIONQUANTITY"+i    : str(p["QUANTITY"]),
            "DONATIONUNITPRICE"+i   : format_currency_no_symbol(l, p["UNITPRICE"]),
            "DONATIONAMOUNT"+i      : format_currency_no_symbol(l, p["DONATION"]),
            "DONATIONCOMMENTS"+i    : p["COMMENTS"],
            "DONATIONCOMMENTSFW"+i  : fw(p["COMMENTS"]),
            "DONATIONGIFTAID"+i     : p["ISGIFTAIDNAME"],
            "DONATIONCREATEDBY"+i   : p["CREATEDBY"],
            "DONATIONCREATEDBYNAME"+i:  p["CREATEDBY"],
            "DONATIONCREATEDDATE"+i : python2display(l, p["CREATEDDATE"]),
            "DONATIONLASTCHANGEDBY"+i : p["LASTCHANGEDBY"],
            "DONATIONLASTCHANGEDBYNAME"+i : p["LASTCHANGEDBY"],
            "DONATIONLASTCHANGEDDATE"+i : python2display(l, p["LASTCHANGEDDATE"]),
            "PAYMENTID"+i           : str(p["ID"]),
            "PAYMENTTYPE"+i         : p["DONATIONNAME"],
            "PAYMENTMETHOD"+i       : p["PAYMENTNAME"],
            "PAYMENTDATE"+i         : python2display(l, p["DATE"]),
            "PAYMENTDATEDUE"+i      : python2display(l, p["DATEDUE"]),
            "PAYMENTQUANTITY"+i    : str(p["QUANTITY"]),
            "PAYMENTUNITPRICE"+i   : format_currency_no_symbol(l, p["UNITPRICE"]),
            "PAYMENTAMOUNT"+i       : format_currency_no_symbol(l, p["DONATION"]),
            "PAYMENTCOMMENTS"+i     : p["COMMENTS"],
            "PAYMENTCOMMENTSFW"+i   : fw(p["COMMENTS"]),
            "PAYMENTGIFTAID"+i      : p["ISGIFTAIDNAME"],
            "PAYMENTVAT"+i          : asm3.utils.iif(p["ISVAT"] == 1, _("Yes", l), _("No", l)),
            "PAYMENTTAX"+i          : asm3.utils.iif(p["ISVAT"] == 1, _("Yes", l), _("No", l)),
            "PAYMENTVATRATE"+i      : "%0.2f" % asm3.utils.cfloat(p["VATRATE"]),
            "PAYMENTTAXRATE"+i      : "%0.2f" % asm3.utils.cfloat(p["VATRATE"]),
            "PAYMENTVATAMOUNT"+i    : format_currency_no_symbol(l, p["VATAMOUNT"]),
            "PAYMENTTAXAMOUNT"+i    : format_currency_no_symbol(l, p["VATAMOUNT"]),
            "PAYMENTCREATEDBY"+i    : p["CREATEDBY"],
            "PAYMENTCREATEDBYNAME"+i: p["CREATEDBY"],
            "PAYMENTCREATEDDATE"+i  : python2display(l, p["CREATEDDATE"]),
            "PAYMENTLASTCHANGEDBY"+i: p["LASTCHANGEDBY"],
            "PAYMENTLASTCHANGEDBYNAME"+i : p["LASTCHANGEDBY"],
            "PAYMENTLASTCHANGEDDATE"+i : python2display(l, p["LASTCHANGEDDATE"]),
            "PAYMENTANIMALNAME"+i   : p["ANIMALNAME"],
            "PAYMENTANIMALSHELTERCODE"+i : p["SHELTERCODE"],
            "PAYMENTANIMALSHORTCODE"+i : p["SHORTCODE"],
            "PAYMENTPERSONNAME"+i   : p["OWNERNAME"],
            "PAYMENTPERSONADDRESS"+i : p["OWNERADDRESS"],
            "PAYMENTPERSONTOWN"+i   : p["OWNERTOWN"],
            "PAYMENTPERSONCITY"+i   : p["OWNERTOWN"],
            "PAYMENTPERSONCOUNTY"+i  : p["OWNERCOUNTY"],
            "PAYMENTPERSONSTATE"+i  : p["OWNERCOUNTY"],
            "PAYMENTPERSONPOSTCODE"+i : p["OWNERPOSTCODE"],
            "PAYMENTPERSONZIPCODE"+i : p["OWNERPOSTCODE"]
        }
        tags.update(x)
        if i == "": return # Don't add a total for the compatibility row
        if p["VATRATE"] > totals["taxrate"]:
            totals["taxrate"] = p["VATRATE"]
        if p["DATE"] is not None: 
            totals["received"] += asm3.utils.cint(p["DONATION"])
            totals["vat"] += asm3.utils.cint(p["VATAMOUNT"])
            totals["total"] += asm3.utils.cint(p["VATAMOUNT"]) + asm3.utils.cint(p["DONATION"])
        if p["DATE"] is None: 
            totals["due"] += asm3.utils.cint(p["DONATION"])
    # Add a copy of the donation tags without an index for compatibility
    if len(donations) > 0:
        add_to_tags("", donations[0]) 
    for i, d in enumerate(donations):
        add_to_tags(str(i+1), d)
    tags["PAYMENTTOTALDUE"] = format_currency_no_symbol(l, totals["due"])
    tags["PAYMENTTOTALRECEIVED"] = format_currency_no_symbol(l, totals["received"])
    tags["PAYMENTTOTALVATRATE"] = "%0.2f" % totals["taxrate"]
    tags["PAYMENTTOTALTAXRATE"] = "%0.2f" % totals["taxrate"]
    tags["PAYMENTTOTALVAT"] = format_currency_no_symbol(l, totals["vat"])
    tags["PAYMENTTOTALTAX"] = format_currency_no_symbol(l, totals["vat"])
    tags["PAYMENTTOTAL"] = format_currency_no_symbol(l, totals["total"])
    return tags

def foundanimal_tags(dbo, a):
    """
    Generates a list of tags from a foundanimal result (asm3.lostfound.get_foundanimal)
    """
    l = dbo.locale
    tags = {
        "ID":                       asm3.utils.padleft(a["ID"], 6),
        "DATEREPORTED":             python2display(l, a["DATEREPORTED"]),
        "DATEFOUND":                python2display(l, a["DATEFOUND"]),
        "DATERETURNED":             python2display(l, a["RETURNTOOWNERDATE"]),
        "AGEGROUP":                 a["AGEGROUP"],
        "FEATURES":                 a["DISTFEAT"],
        "AREAFOUND":                a["AREAFOUND"],
        "AREAPOSTCODE":             a["AREAPOSTCODE"],
        "COMMENTS":                 a["COMMENTS"],
        "SPECIESNAME":              a["SPECIESNAME"],
        "BREEDNAME":                a["BREEDNAME"],
        "BASECOLOURNAME":           a["BASECOLOURNAME"],
        "BASECOLORNAME":            a["BASECOLOURNAME"],
        "SEX":                      a["SEXNAME"],
        "DOCUMENTIMGLINK"       : "<img height=\"200\" src=\"" + asm3.html.doc_img_src(dbo, a) + "\" >",
        "DOCUMENTIMGLINK200"    : "<img height=\"200\" src=\"" + asm3.html.doc_img_src(dbo, a) + "\" >",
        "DOCUMENTIMGLINK300"    : "<img height=\"300\" src=\"" + asm3.html.doc_img_src(dbo, a) + "\" >",
        "DOCUMENTIMGLINK400"    : "<img height=\"400\" src=\"" + asm3.html.doc_img_src(dbo, a) + "\" >",
        "DOCUMENTIMGLINK500"    : "<img height=\"500\" src=\"" + asm3.html.doc_img_src(dbo, a) + "\" >"
    }

    # Additional fields
    tags.update(additional_field_tags(dbo, asm3.additional.get_additional_fields(dbo, a["ID"], "foundanimal")))

    # Logs
    d = {
        "LOGNAME":            "LOGTYPENAME",
        "LOGDATE":            "d:DATE",
        "LOGTIME":            "t:DATE",
        "LOGCOMMENTS":        "COMMENTS",
        "LOGCREATEDBY":       "CREATEDBY"
    }
    tags.update(table_tags(dbo, d, asm3.log.get_logs(dbo, asm3.log.FOUNDANIMAL, a["ID"], 0, asm3.log.ASCENDING), "LOGTYPENAME", "DATE", "DATE"))
    return tags

def lostanimal_tags(dbo, a):
    """
    Generates a list of tags from a lostanimal result (asm3.lostfound.get_lostanimal)
    """
    l = dbo.locale
    tags = {
        "ID":                       asm3.utils.padleft(a["ID"], 6),
        "DATEREPORTED":             python2display(l, a["DATEREPORTED"]),
        "DATELOST":                 python2display(l, a["DATELOST"]),
        "DATEFOUND":                python2display(l, a["DATEFOUND"]),
        "AGEGROUP":                 a["AGEGROUP"],
        "FEATURES":                 a["DISTFEAT"],
        "AREALOST":                 a["AREALOST"],
        "AREAPOSTCODE":             a["AREAPOSTCODE"],
        "COMMENTS":                 a["COMMENTS"],
        "SPECIESNAME":              a["SPECIESNAME"],
        "BREEDNAME":                a["BREEDNAME"],
        "BASECOLOURNAME":           a["BASECOLOURNAME"],
        "BASECOLORNAME":            a["BASECOLOURNAME"],
        "SEX":                      a["SEXNAME"],
        "DOCUMENTIMGLINK"       : "<img height=\"200\" src=\"" + asm3.html.doc_img_src(dbo, a) + "\" >",
        "DOCUMENTIMGLINK200"    : "<img height=\"200\" src=\"" + asm3.html.doc_img_src(dbo, a) + "\" >",
        "DOCUMENTIMGLINK300"    : "<img height=\"300\" src=\"" + asm3.html.doc_img_src(dbo, a) + "\" >",
        "DOCUMENTIMGLINK400"    : "<img height=\"400\" src=\"" + asm3.html.doc_img_src(dbo, a) + "\" >",
        "DOCUMENTIMGLINK500"    : "<img height=\"500\" src=\"" + asm3.html.doc_img_src(dbo, a) + "\" >"
    }

    # Additional fields
    tags.update(additional_field_tags(dbo, asm3.additional.get_additional_fields(dbo, a["ID"], "lostanimal")))

    # Logs
    d = {
        "LOGNAME":            "LOGTYPENAME",
        "LOGDATE":            "d:DATE",
        "LOGTIME":            "t:DATE",
        "LOGCOMMENTS":        "COMMENTS",
        "LOGCREATEDBY":       "CREATEDBY"
    }
    tags.update(table_tags(dbo, d, asm3.log.get_logs(dbo, asm3.log.LOSTANIMAL, a["ID"], 0, asm3.log.ASCENDING), "LOGTYPENAME", "DATE", "DATE"))
    return tags

def licence_tags(dbo, li):
    """
    Generates a list of tags from a licence result 
    (from anything using asm3.financial.get_licence_query)
    """
    l = dbo.locale
    tags = {
        "LICENCETYPENAME":      li["LICENCETYPENAME"],
        "LICENCENUMBER":        li["LICENCENUMBER"],
        "LICENCEFEE":           format_currency_no_symbol(l, li["LICENCEFEE"]),
        "LICENCEISSUED":        python2display(l, li["ISSUEDATE"]),
        "LICENCEEXPIRES":       python2display(l, li["EXPIRYDATE"]),
        "LICENCECOMMENTS":      li["COMMENTS"],
        "LICENSETYPENAME":      li["LICENCETYPENAME"],
        "LICENSENUMBER":        li["LICENCENUMBER"],
        "LICENSEFEE":           format_currency_no_symbol(l, li["LICENCEFEE"]),
        "LICENSEISSUED":        python2display(l, li["ISSUEDATE"]),
        "LICENSEEXPIRES":       python2display(l, li["EXPIRYDATE"]),
        "LICENSECOMMENTS":      li["COMMENTS"]
    }
    return tags

def movement_tags(dbo, m):
    """
    Generates a list of tags from a movement result
    (anything using asm3.movement.get_movement_query)
    """
    l = dbo.locale
    tags = {
        "MOVEMENTTYPE":                 m["MOVEMENTNAME"],
        "MOVEMENTDATE":                 python2display(l, m["MOVEMENTDATE"]),
        "MOVEMENTNUMBER":               m["ADOPTIONNUMBER"],
        "ADOPTIONNUMBER":               m["ADOPTIONNUMBER"],
        "ADOPTIONDONATION":             format_currency_no_symbol(l, m["DONATION"]),
        "MOVEMENTPAYMENTTOTAL":         format_currency_no_symbol(l, m["DONATION"]),
        "INSURANCENUMBER":              m["INSURANCENUMBER"],
        "RETURNDATE":                   python2display(l, m["RETURNDATE"]),
        "RETURNNOTES":                  m["REASONFORRETURN"],
        "RETURNREASON":                 asm3.utils.iif(m["RETURNDATE"] is not None, m["RETURNEDREASONNAME"], ""),
        "RESERVATIONDATE":              m["RESERVATIONDATE"],
        "RESERVATIONCANCELLEDDATE":     m["RESERVATIONCANCELLEDDATE"],
        "RESERVATIONSTATUS":            m["RESERVATIONSTATUSNAME"],
        "MOVEMENTISTRIAL":              asm3.utils.iif(m["ISTRIAL"] == 1, _("Yes", l), _("No", l)),
        "MOVEMENTISPERMANENTFOSTER":    asm3.utils.iif(m["ISPERMANENTFOSTER"] == 1, _("Yes", l), _("No", l)),
        "MOVEMENTCOMMENTS":             m["COMMENTS"],
        "MOVEMENTCREATEDBY":            m["CREATEDBY"],
        "MOVEMENTLASTCHANGEDBY":        m["LASTCHANGEDBY"],
        "MOVEMENTCREATEDDATE":          python2display(l, m["CREATEDDATE"]),
        "MOVEMENTLASTCHANGEDDATE":      python2display(l, m["LASTCHANGEDDATE"]),
        "ADOPTIONCREATEDBY":            m["CREATEDBY"],
        "ADOPTIONLASTCHANGEDBY":        m["LASTCHANGEDBY"],
        "ADOPTIONCREATEDDATE":          python2display(l, m["CREATEDDATE"]),
        "ADOPTIONLASTCHANGEDDATE":      python2display(l, m["LASTCHANGEDDATE"]),
        "ADOPTIONDATE":                 asm3.utils.iif(m["MOVEMENTTYPE"] == asm3.movement.ADOPTION, python2display(l, m["MOVEMENTDATE"]), ""),
        "FOSTEREDDATE":                 asm3.utils.iif(m["MOVEMENTTYPE"] == asm3.movement.FOSTER, python2display(l, m["MOVEMENTDATE"]), ""),
        "TRANSFERDATE":                 asm3.utils.iif(m["MOVEMENTTYPE"] == asm3.movement.TRANSFER, python2display(l, m["MOVEMENTDATE"]), ""),
        "TRIALENDDATE":                 asm3.utils.iif(m["MOVEMENTTYPE"] == asm3.movement.ADOPTION, python2display(l, m["TRIALENDDATE"]), "")
    }
    return tags    

def clinic_tags(dbo, c):
    """
    Generates a list of tags from a clinic result (asm3.clinic.get_appointment)
    """
    l = dbo.locale
    tags = {
        "ID":                   asm3.utils.padleft(c.ID, 6),
        "APPOINTMENTFOR"        : asm3.users.get_real_name(dbo, c.APPTFOR),
        "APPOINTMENTDATE"       : python2display(l, c.DATETIME),
        "APPOINTMENTTIME"       : format_time(c.DATETIME),
        "STATUS"                : c.CLINICSTATUSNAME,
        "ARRIVEDDATE"           : python2display(l, c.ARRIVEDDATETIME),
        "ARRIVEDTIME"           : format_time(c.ARRIVEDDATETIME),
        "WITHVETDATE"           : python2display(l, c.WITHVETDATETIME),
        "WITHVETTIME"           : format_time(c.WITHVETDATETIME),
        "COMPLETEDDATE"         : python2display(l, c.COMPLETEDDATETIME),
        "COMPLETEDTIME"         : format_time(c.COMPLETEDDATETIME),
        "REASONFORAPPOINTMENT"  : c.REASONFORAPPOINTMENT,
        "APPOINTMENTCOMMENTS"   : c.COMMENTS,
        "INVOICEAMOUNT"         : format_currency_no_symbol(l, c.AMOUNT),
        "INVOICEVATAMOUNT"      : format_currency_no_symbol(l, c.VATAMOUNT),
        "INVOICETAXAMOUNT"      : format_currency_no_symbol(l, c.VATAMOUNT),
        "INVOICEVATRATE"        : c.VATRATE,
        "INVOICETAXRATE"        : c.VATRATE,
        "INVOICETOTAL"          : format_currency_no_symbol(l, c.AMOUNT + c.VATAMOUNT),
    }

    # Invoice items
    d = {
        "CLINICINVOICEAMOUNT"       : "c:AMOUNT",
        "CLINICINVOICEDESCRIPTION"  : "DESCRIPTION"
    }
    tags.update(table_tags(dbo, d, asm3.clinic.get_invoice_items(dbo, c.ID)))
    return tags

def person_tags(dbo, p, includeImg=False):
    """
    Generates a list of tags from a person result (the deep type from
    calling asm3.person.get_person)
    """
    l = dbo.locale
    tags = { 
        "OWNERID"               : str(p["ID"]),
        "OWNERCODE"             : p["OWNERCODE"],
        "OWNERTITLE"            : p["OWNERTITLE"],
        "TITLE"                 : p["OWNERTITLE"],
        "OWNERINITIALS"         : p["OWNERINITIALS"],
        "INITIALS"              : p["OWNERINITIALS"],
        "OWNERFORENAMES"        : p["OWNERFORENAMES"],
        "FORENAMES"             : p["OWNERFORENAMES"],
        "OWNERFIRSTNAMES"       : p["OWNERFORENAMES"],
        "FIRSTNAMES"            : p["OWNERFORENAMES"],
        "OWNERSURNAME"          : p["OWNERSURNAME"],
        "SURNAME"               : p["OWNERSURNAME"],
        "OWNERLASTNAME"         : p["OWNERSURNAME"],
        "LASTNAME"              : p["OWNERSURNAME"],
        "OWNERNAME"             : p["OWNERNAME"],
        "NAME"                  : p["OWNERNAME"],
        "OWNERADDRESS"          : p["OWNERADDRESS"],
        "ADDRESS"               : p["OWNERADDRESS"],
        "OWNERTOWN"             : p["OWNERTOWN"],
        "TOWN"                  : p["OWNERTOWN"],
        "OWNERCOUNTY"           : p["OWNERCOUNTY"],
        "COUNTY"                : p["OWNERCOUNTY"],
        "OWNERCITY"             : p["OWNERTOWN"],
        "CITY"                  : p["OWNERTOWN"],
        "OWNERSTATE"            : p["OWNERCOUNTY"],
        "STATE"                 : p["OWNERCOUNTY"],
        "OWNERPOSTCODE"         : p["OWNERPOSTCODE"],
        "POSTCODE"              : p["OWNERPOSTCODE"],
        "OWNERZIPCODE"          : p["OWNERPOSTCODE"],
        "ZIPCODE"               : p["OWNERPOSTCODE"],
        "HOMETELEPHONE"         : p["HOMETELEPHONE"],
        "WORKTELEPHONE"         : p["WORKTELEPHONE"],
        "MOBILETELEPHONE"       : p["MOBILETELEPHONE"],
        "CELLTELEPHONE"         : p["MOBILETELEPHONE"],
        "EMAILADDRESS"          : p["EMAILADDRESS"],
        "JURISDICTION"          : p["JURISDICTIONNAME"],
        "OWNERCOMMENTS"         : p["COMMENTS"],
        "OWNERFLAGS"            : asm3.utils.nulltostr(p["ADDITIONALFLAGS"]).replace("|", ", "),
        "OWNERCREATEDBY"        : p["CREATEDBY"],
        "OWNERCREATEDBYNAME"    : p["CREATEDBY"],
        "OWNERCREATEDDATE"      : python2display(l, p["CREATEDDATE"]),
        "OWNERLASTCHANGEDBY"    : p["LASTCHANGEDBY"],
        "OWNERLASTCHANGEDBYNAME" : p["LASTCHANGEDBY"],
        "OWNERLASTCHANGEDDATE"  : python2display(l, p["LASTCHANGEDDATE"]),
        "IDCHECK"               : asm3.utils.iif(p["IDCHECK"] == 1, _("Yes", l), _("No", l)),
        "HOMECHECKEDBYNAME"     : p["HOMECHECKEDBYNAME"],
        "HOMECHECKEDBYEMAIL"    : p["HOMECHECKEDBYEMAIL"],
        "HOMECHECKEDBYHOMETELEPHONE": p["HOMECHECKEDBYHOMETELEPHONE"],
        "HOMECHECKEDBYMOBILETELEPHONE": p["HOMECHECKEDBYMOBILETELEPHONE"],
        "HOMECHECKEDBYCELLTELEPHONE": p["HOMECHECKEDBYMOBILETELEPHONE"],
        "MEMBERSHIPNUMBER"      : p["MEMBERSHIPNUMBER"],
        "MEMBERSHIPEXPIRYDATE"  : python2display(l, p["MEMBERSHIPEXPIRYDATE"]),
    }

    if includeImg:
        tags["DOCUMENTIMGSRC"] = asm3.html.doc_img_src(dbo, p)
        tags["DOCUMENTIMGLINK"] = "<img height=\"200\" src=\"" + asm3.html.doc_img_src(dbo, p) + "\" >"
        tags["DOCUMENTIMGLINK200"] = "<img height=\"200\" src=\"" + asm3.html.doc_img_src(dbo, p) + "\" >"
        tags["DOCUMENTIMGLINK300"] = "<img height=\"300\" src=\"" + asm3.html.doc_img_src(dbo, p) + "\" >"
        tags["DOCUMENTIMGLINK400"] = "<img height=\"400\" src=\"" + asm3.html.doc_img_src(dbo, p) + "\" >"
        tags["DOCUMENTIMGLINK500"] = "<img height=\"500\" src=\"" + asm3.html.doc_img_src(dbo, p) + "\" >"

    # Additional fields
    tags.update(additional_field_tags(dbo, asm3.additional.get_additional_fields(dbo, p["ID"], "person")))

    # Citations
    d = {
        "CITATIONNAME":         "CITATIONNAME",
        "CITATIONDATE":         "d:CITATIONDATE",
        "CITATIONCOMMENTS":     "COMMENTS",
        "FINEAMOUNT":           "c:FINEAMOUNT",
        "FINEDUEDATE":          "d:FINEDUEDATE",
        "FINEPAIDDATE":         "d:FINEPAIDDATE"
    }
    tags.update(table_tags(dbo, d, asm3.financial.get_person_citations(dbo, p["ID"]), "CITATIONNAME", "CITATIONDATE", "FINEPAIDDATE"))

    # Logs
    d = {
        "PERSONLOGNAME":            "LOGTYPENAME",
        "PERSONLOGDATE":            "d:DATE",
        "PERSONLOGTIME":            "t:DATE",
        "PERSONLOGCOMMENTS":        "COMMENTS",
        "PERSONLOGCREATEDBY":       "CREATEDBY"
    }
    tags.update(table_tags(dbo, d, asm3.log.get_logs(dbo, asm3.log.PERSON, p["ID"], 0, asm3.log.ASCENDING), "LOGTYPENAME", "DATE", "DATE"))

    # Trap loans
    d = {
        "TRAPTYPENAME":             "TRAPTYPENAME",
        "TRAPLOANDATE":             "d:LOANDATE",
        "TRAPDEPOSITAMOUNT":        "c:DEPOSITAMOUNT",
        "TRAPDEPOSITRETURNDATE":    "d:DEPOSITRETURNDATE",
        "TRAPNUMBER":               "TRAPNUMBER",
        "TRAPRETURNDUEDATE":        "d:RETURNDUEDATE",
        "TRAPRETURNDATE":           "d:RETURNDATE",
        "TRAPCOMMENTS":             "COMMENTS"
    }
    tags.update(table_tags(dbo, d, asm3.animalcontrol.get_person_traploans(dbo, p["ID"], asm3.animalcontrol.ASCENDING), "TRAPTYPENAME", "RETURNDUEDATE", "RETURNDATE"))

    return tags

def transport_tags(dbo, transports):
    """
    Generates a list of tags from a list of transports.
    transports: a list of transport records
    """
    l = dbo.locale
    tags = {}
    def add_to_tags(i, t): 
        x = { 
            "TRANSPORTID"+i:              str(t["ID"]),
            "TRANSPORTTYPE"+i:            t["TRANSPORTTYPENAME"],
            "TRANSPORTDRIVERNAME"+i:      t["DRIVEROWNERNAME"], 

            "TRANSPORTPICKUPNAME"+i:      t["PICKUPOWNERNAME"], 
            "TRANSPORTPICKUPDATETIME"+i:  python2display(l, t["PICKUPDATETIME"]),
            "TRANSPORTPICKUPADDRESS"+i:   t["PICKUPADDRESS"],
            "TRANSPORTPICKUPTOWN"+i:      t["PICKUPTOWN"],
            "TRANSPORTPICKUPCITY"+i:      t["PICKUPTOWN"],
            "TRANSPORTPICKUPCOUNTY"+i:    t["PICKUPCOUNTY"],
            "TRANSPORTPICKUPSTATE"+i:     t["PICKUPCOUNTY"],
            "TRANSPORTPICKUPZIPCODE"+i:   t["PICKUPPOSTCODE"],
            "TRANSPORTPICKUPCOUNTRY"+i:   t["PICKUPCOUNTRY"],
            "TRANSPORTPICKUPPOSTCODE"+i:  t["PICKUPPOSTCODE"],
            "TRANSPORTPICKUPEMAIL"+i:     t["PICKUPEMAILADDRESS"],
            "TRANSPORTPICKUPHOMEPHONE"+i: t["PICKUPHOMETELEPHONE"],
            "TRANSPORTPICKUPWORKPHONE"+i: t["PICKUPWORKTELEPHONE"],
            "TRANSPORTPICKUPMOBILEPHONE"+i: t["PICKUPMOBILETELEPHONE"],
            "TRANSPORTPICKUPCELLPHONE"+i: t["PICKUPMOBILETELEPHONE"],

            "TRANSPORTDROPOFFNAME"+i:     t["DROPOFFOWNERNAME"], 
            "TRANSPORTDROPOFFDATETIME"+i: python2display(l, t["DROPOFFDATETIME"]),
            "TRANSPORTDROPOFFADDRESS"+i:  t["DROPOFFADDRESS"],
            "TRANSPORTDROPOFFTOWN"+i:     t["DROPOFFTOWN"],
            "TRANSPORTDROPOFFCITY"+i:     t["DROPOFFTOWN"],
            "TRANSPORTDROPOFFCOUNTY"+i:   t["DROPOFFCOUNTY"],
            "TRANSPORTDROPOFFSTATE"+i:    t["DROPOFFCOUNTY"],
            "TRANSPORTDROPOFFZIPCODE"+i:  t["DROPOFFPOSTCODE"],
            "TRANSPORTDROPOFFPOSTCODE"+i: t["DROPOFFPOSTCODE"],
            "TRANSPORTDROPOFFCOUNTRY"+i:  t["DROPOFFCOUNTRY"],
            "TRANSPORTDROPOFFEMAIL"+i:    t["DROPOFFEMAILADDRESS"],
            "TRANSPORTDROPOFFHOMEPHONE"+i: t["DROPOFFHOMETELEPHONE"],
            "TRANSPORTDROPOFFWORKPHONE"+i: t["DROPOFFWORKTELEPHONE"],
            "TRANSPORTDROPOFFMOBILEPHONE"+i: t["DROPOFFMOBILETELEPHONE"],
            "TRANSPORTDROPOFFCELLPHONE"+i: t["DROPOFFMOBILETELEPHONE"],

            "TRANSPORTMILES"+i:           str(t["MILES"]),
            "TRANSPORTCOST"+i:            format_currency_no_symbol(l, t["COST"]),
            "TRANSPORTCOSTPAIDDATE"+i:    python2display(l, t["COSTPAIDDATE"]),
            "TRANSPORTCOMMENTS"+i:        t["COMMENTS"],

            "TRANSPORTANIMALNAME"+i:      t["ANIMALNAME"],
            "TRANSPORTSHELTERCODE"+i:     t["SHELTERCODE"],
            "TRANSPORTSHORTCODE"+i:       t["SHORTCODE"],
            "TRANSPORTSPECIES"+i:         t["SPECIESNAME"],
            "TRANSPORTBREED"+i:           t["BREEDNAME"],
            "TRANSPORTSEX"+i:             t["SEX"],
        }
        tags.update(x)
    # Add a copy of the transport tags without an index
    if len(transports) > 0:
        add_to_tags("", transports[0]) 
    for i, t in enumerate(transports):
        add_to_tags(str(i+1), t)
    return tags

def waitinglist_tags(dbo, a):
    """
    Generates a list of tags from a waiting list result (asm3.waitinglist.get_waitinglist_by_id)
    """
    l = dbo.locale
    tags = {
        "ID":                       asm3.utils.padleft(a["ID"], 6),
        "DATEPUTONLIST":            python2display(l, a["DATEPUTONLIST"]),
        "DATEREMOVEDFROMLIST":      python2display(l, a["DATEREMOVEDFROMLIST"]),
        "DATEOFLASTOWNERCONTACT":   python2display(l, a["DATEOFLASTOWNERCONTACT"]),
        "SIZE":                     a["SIZENAME"],
        "SPECIESNAME":              a["SPECIESNAME"],
        "DESCRIPTION":              a["ANIMALDESCRIPTION"],
        "REASONFORWANTINGTOPART":   a["REASONFORWANTINGTOPART"],
        "REASONFORREMOVAL":         a["REASONFORREMOVAL"],
        "CANAFFORDDONATION":        asm3.utils.iif(a["CANAFFORDDONATION"] == 1, _("Yes", l), _("No", l)),
        "URGENCY":                  a["URGENCYNAME"],
        "COMMENTS":                 a["COMMENTS"],
        "DOCUMENTIMGLINK"       : "<img height=\"200\" src=\"" + asm3.html.doc_img_src(dbo, a) + "\" >",
        "DOCUMENTIMGLINK200"    : "<img height=\"200\" src=\"" + asm3.html.doc_img_src(dbo, a) + "\" >",
        "DOCUMENTIMGLINK300"    : "<img height=\"300\" src=\"" + asm3.html.doc_img_src(dbo, a) + "\" >",
        "DOCUMENTIMGLINK400"    : "<img height=\"400\" src=\"" + asm3.html.doc_img_src(dbo, a) + "\" >",
        "DOCUMENTIMGLINK500"    : "<img height=\"500\" src=\"" + asm3.html.doc_img_src(dbo, a) + "\" >"
    }

    # Additional fields
    tags.update(additional_field_tags(dbo, asm3.additional.get_additional_fields(dbo, a["ID"], "waitinglist")))

    # Logs
    d = {
        "LOGNAME":            "LOGTYPENAME",
        "LOGDATE":            "d:DATE",
        "LOGTIME":            "t:DATE",
        "LOGCOMMENTS":        "COMMENTS",
        "LOGCREATEDBY":       "CREATEDBY"
    }
    tags.update(table_tags(dbo, d, asm3.log.get_logs(dbo, asm3.log.WAITINGLIST, a["ID"], 0, asm3.log.ASCENDING), "LOGTYPENAME", "DATE", "DATE"))
    return tags

def append_tags(tags1, tags2):
    """
    Adds two dictionaries of tags together and returns
    a new dictionary containing both sets.
    """
    tags = {}
    tags.update(tags1)
    tags.update(tags2)
    return tags

def html_table(l, rows, cols):
    """
    Generates an HTML table for TinyMCE from rows, choosing the cols.
    cols is a list of tuples containing the field name from rows and a localised column name for output.
    Eg: ( ( "ID", "Text for ID field" ) )
    """
    h = []
    h.append("<table border=\"1\">")
    h.append("<thead><tr>")
    for colfield, coltext in cols:
        h.append("<th>%s</th>" % coltext)
    h.append("</tr></thead>")
    h.append("<tbody>")
    for r in rows:
        h.append("<tr>")
        for colfield, coltext in cols:
            if asm3.utils.is_date(r[colfield]):
                h.append("<td>%s</td>" % python2display(l, r[colfield]))
            elif r[colfield] is None:
                h.append("<td></td>")
            elif asm3.utils.is_str(r[colfield]) or asm3.utils.is_unicode(r[colfield]):
                h.append("<td>%s</td>" % r[colfield].replace("\n", "<br/>"))
            else:
                h.append("<td>%s</td>" % r[colfield])
        h.append("</tr>")
    h.append("</tbody>")
    h.append("</table>")
    return "".join(h)

def table_get_value(l, row, k):
    """
    Returns row[k], looking for a type prefix in k -
    c: currency, d: date, t: time, y: yesno, f: float
    """
    if k.find("d:") != -1: 
        s = python2display(l, row[k.replace("d:", "")])
    elif k.find("t:") != -1: 
        s = format_time(row[k.replace("t:", "")])
    elif k.find("c:") != -1:
        s = format_currency_no_symbol(l, row[k.replace("c:", "")])
    elif k.find("y:") != -1:
        s = asm3.utils.iif(row[k.replace("y:", "")] == 1, _("Yes", l), _("No", l))
    elif k.find("f:") != -1:
        s = "%0.2f" % asm3.utils.cfloat(row[k.replace("f:", "")])
    else:
        s = str(row[k])
    return s

def table_tags(dbo, d, rows, typefield = "", recentduefield = "", recentgivenfield = ""):
    """
    For a collection of table rows, generates the LAST/DUE/RECENT and indexed tags.

    d: A dictionary of tag names to field expressions. If the field is
       preceded with d:, it is formatted as a date, c: a currency
       eg: { "VACCINATIONNAME" : "VACCINATIONTYPE", "VACCINATIONREQUIRED", "d:DATEREQUIRED" }

    typefield: The name of the field in rows that contains the type for
       creating tags with the type as a suffix

    recentduefield: The name of the field in rows that contains the date
        the last thing was was due for DUE tags.

    recentgivenfield: The name of the field in rows that contains the date
        the last thing was received/given for RECENT tags.

    rows: The table rows
    """
    l = dbo.locale
    tags = {}
    uniquetypes = {}
    recentdue = {}
    recentgiven = {}

    # Go forwards through the rows
    for i, r in enumerate(rows, 1):
        
        # Create the indexed tags
        for k, v in d.items():
            tags[k + str(i)] = table_get_value(l, r, v)

        # Type suffixed tags
        if typefield != "":
            t = r[typefield]

            # If the type is somehow null, we can't do anything
            if t is None: continue

            # Is this the first of this type we've seen?
            # If so, create the tags with type as a suffix
            if t not in uniquetypes:
                uniquetypes[t] = r
                t = t.upper().replace(" ", "").replace("/", "")
                for k, v in d.items():
                    tags[k + t] = table_get_value(l, r, v)

    # Go backwards through rows
    for i, r in enumerate(reversed(rows), 1):

        # Create reversed index tags
        for k, v in d.items():
            tags[k + "LAST" + str(i)] = table_get_value(l, r, v)

        # Due suffixed tags
        if recentduefield != "":
            t = r[typefield]
            # If the type is somehow null, we can't do anything
            if t is None: continue
            # Is this the first type with a due date and blank given date we've seen?
            # If so, create the tags with due as a suffix
            if t not in recentdue and r[recentduefield] is not None and r[recentgivenfield] is None:
                recentdue[t] = r
                t = t.upper().replace(" ", "").replace("/", "")
                for k, v in d.items():
                    tags[k + "DUE" + t] = table_get_value(l, r, v)

        # Recent suffixed tags
        if recentgivenfield != "":
            t = r[typefield]
            # If the type is somehow null, we can't do anything
            if t is None: continue
            # Is this the first type with a date we've seen?
            # If so, create the tags with recent as a suffix
            if t not in recentgiven and r[recentgivenfield] is not None:
                recentgiven[t] = r
                t = t.upper().replace(" ", "").replace("/", "")
                for k, v in d.items():
                    tags[k + "RECENT" + t] = table_get_value(l, r, v)
    return tags

def substitute_tags_plain(searchin, tags):
    """
    Substitutes the dictionary of tags in "tags" for any found in
    "searchin". This is a convenience method for plain text substitution
    with << >> opener/closers and no XML escaping.
    """
    return substitute_tags(searchin, tags, False, "<<", ">>")

def substitute_tags(searchin, tags, use_xml_escaping = True, opener = "&lt;&lt;", closer = "&gt;&gt;"):
    """
    Substitutes the dictionary of tags in "tags" for any found
    in "searchin". opener and closer denote the start of a tag,
    if use_xml_escaping is set to true, then tags are XML escaped when
    output and opener/closer are escaped.
    """
    if not use_xml_escaping:
        opener = opener.replace("&lt;", "<").replace("&gt;", ">")
        closer = closer.replace("&lt;", "<").replace("&gt;", ">")

    s = searchin
    sp = s.find(opener)
    while sp != -1:
        ep = s.find(closer, sp + len(opener))
        if ep != -1:
            matchtag = s[sp + len(opener):ep].upper()
            newval = ""
            if matchtag in tags:
                newval = tags[matchtag]
                if newval is not None:
                    newval = str(newval)
                    # Escape xml entities unless the replacement tag is an image
                    # or it contains HTML entities or <br> tags or <table> tags
                    if use_xml_escaping and \
                       not newval.lower().startswith("<img") and \
                       not newval.lower().find("&#") != -1 and \
                       not newval.lower().find("<br") != -1 and \
                       not newval.lower().find("<table") != -1:
                        newval = newval.replace("&", "&amp;")
                        newval = newval.replace("<", "&lt;")
                        newval = newval.replace(">", "&gt;")
            s = s[0:sp] + str(newval) + s[ep + len(closer):]
            sp = s.find(opener, sp)
        else:
            # No end marker for this tag, stop processing
            break
    return s

def substitute_template(dbo, templateid, tags, imdata = None):
    """
    Reads the template specified by id "template" and substitutes
    according to the tags in "tags". Returns the built file.
    imdata is the preferred image for the record and since html uses
    URLs, only applies to ODT templates.
    """
    templatedata = asm3.template.get_document_template_content(dbo, templateid) # bytes
    templatename = asm3.template.get_document_template_name(dbo, templateid)
    if templatename.endswith(".html"):
        # Translate any user signature placeholder
        templatedata = asm3.utils.bytes2str(templatedata).replace("signature:user", "&lt;&lt;UserSignatureSrc&gt;&gt;")
        return substitute_tags(templatedata, tags)
    elif templatename.endswith(".odt"):
        try:
            odt = asm3.utils.bytesio(templatedata)
            zf = zipfile.ZipFile(odt, "r")
            # Load the content.xml file and substitute the tags
            content = asm3.utils.bytes2str(zf.open("content.xml").read())
            content = substitute_tags(content, tags)
            # Write the replacement file
            zo = asm3.utils.bytesio()
            zfo = zipfile.ZipFile(zo, "w", zipfile.ZIP_DEFLATED)
            for info in zf.infolist():
                if info.filename == "content.xml":
                    zfo.writestr("content.xml", asm3.utils.str2bytes(content))
                elif imdata is not None and (info.file_size == 2897 or info.file_size == 7701):
                    # If the image is the old placeholder.jpg or our default nopic.jpg, substitute for the record image
                    zfo.writestr(info.filename, imdata)
                else:
                    zfo.writestr(info.filename, zf.open(info.filename).read())
            zf.close()
            zfo.close()
            # Return the zip data
            return zo.getvalue()
        except Exception as zderr:
            raise asm3.utils.ASMError("Failed generating odt document: %s" % str(zderr))

def generate_animal_doc(dbo, templateid, animalid, username):
    """
    Generates an animal document from a template using animal keys and
    (if a currentowner is available) person keys
    templateid: The ID of the template
    animalid: The animal to generate for
    """
    a = asm3.animal.get_animal(dbo, animalid)
    im = asm3.media.get_image_file_data(dbo, "animal", animalid)[1]
    if a is None: raise asm3.utils.ASMValidationError("%d is not a valid animal ID" % animalid)
    # Only include donations if there isn't an active movement as we'll take care
    # of them below if there is
    tags = animal_tags(dbo, a, includeDonations=(not a["ACTIVEMOVEMENTID"] or a["ACTIVEMOVEMENTID"] == 0))
    # Use the person info from the latest open movement for the animal
    # This will pick up future dated adoptions instead of fosterers (which are still currentowner)
    # as get_animal_movements returns them in descending order of movement date
    has_person_tags = False
    for m in asm3.movement.get_animal_movements(dbo, animalid):
        if m["MOVEMENTDATE"] is not None and m["RETURNDATE"] is None and m["OWNERID"] is not None and m["OWNERID"] != 0:
            has_person_tags = True
            tags = append_tags(tags, person_tags(dbo, asm3.person.get_person(dbo, m["OWNERID"])))
            tags = append_tags(tags, movement_tags(dbo, m))
            md = asm3.financial.get_movement_donations(dbo, m["ID"])
            if len(md) > 0: 
                tags = append_tags(tags, donation_tags(dbo, md))
            break
    # If we didn't have an open movement and there's a reserve, use that as the person
    if not has_person_tags and a["RESERVEDOWNERID"] is not None and a["RESERVEDOWNERID"] != 0:
        tags = append_tags(tags, person_tags(dbo, asm3.person.get_person(dbo, a["RESERVEDOWNERID"])))
        has_person_tags = True
    # If this is a non-shelter animal, use the owner
    if not has_person_tags and a["NONSHELTERANIMAL"] == 1 and a["ORIGINALOWNERID"] is not None and a["ORIGINALOWNERID"] != 0:
        tags = append_tags(tags, person_tags(dbo, asm3.person.get_person(dbo, a["ORIGINALOWNERID"])))
        has_person_tags = True
    tags = append_tags(tags, org_tags(dbo, username))
    return substitute_template(dbo, templateid, tags, im)

def generate_animalcontrol_doc(dbo, templateid, acid, username):
    """
    Generates an animal control incident document from a template
    templateid: The ID of the template
    acid:     The incident id to generate for
    """
    ac = asm3.animalcontrol.get_animalcontrol(dbo, acid)
    if ac is None: raise asm3.utils.ASMValidationError("%d is not a valid incident ID" % acid)
    tags = animalcontrol_tags(dbo, ac)
    tags = append_tags(tags, org_tags(dbo, username))
    return substitute_template(dbo, templateid, tags)

def generate_clinic_doc(dbo, templateid, appointmentid, username):
    """
    Generates a clinic document from a template
    templateid: The ID of the template
    appointmentid: The clinicappointment id to generate for
    """
    c = asm3.clinic.get_appointment(dbo, appointmentid)
    if c is None: raise asm3.utils.ASMValidationError("%d is not a valid clinic appointment ID" % appointmentid)
    tags = clinic_tags(dbo, c)
    a = asm3.animal.get_animal(dbo, c.ANIMALID)
    if a is not None:
        tags = append_tags(tags, animal_tags(dbo, a, includeAdditional=True, includeCosts=False, includeDiet=False, includeDonations=False, \
            includeFutureOwner=False, includeIsVaccinated=False, includeLogs=False, includeMedical=False))
    tags = append_tags(tags, person_tags(dbo, asm3.person.get_person(dbo, c.OWNERID)))
    return substitute_template(dbo, templateid, tags)

def generate_person_doc(dbo, templateid, personid, username):
    """
    Generates a person document from a template
    templateid: The ID of the template
    personid: The person to generate for
    """
    p = asm3.person.get_person(dbo, personid)
    im = asm3.media.get_image_file_data(dbo, "person", personid)[1]
    if p is None: raise asm3.utils.ASMValidationError("%d is not a valid person ID" % personid)
    tags = person_tags(dbo, p, includeImg=True)
    tags = append_tags(tags, org_tags(dbo, username))
    m = asm3.movement.get_person_movements(dbo, personid)
    if len(m) > 0: 
        tags = append_tags(tags, movement_tags(dbo, m[0]))
        tags = append_tags(tags, animal_tags(dbo, asm3.animal.get_animal(dbo, m[0]["ANIMALID"])))
    return substitute_template(dbo, templateid, tags, im)

def generate_donation_doc(dbo, templateid, donationids, username):
    """
    Generates a donation document from a template
    templateid: The ID of the template
    donationids: A list of ids to generate for
    """
    dons = asm3.financial.get_donations_by_ids(dbo, donationids)
    if len(dons) == 0: 
        raise asm3.utils.ASMValidationError("%s does not contain any valid donation IDs" % donationids)
    d = dons[0]
    tags = person_tags(dbo, asm3.person.get_person(dbo, d["OWNERID"]))
    if d["ANIMALID"] is not None and d["ANIMALID"] != 0:
        tags = append_tags(tags, animal_tags(dbo, asm3.animal.get_animal(dbo, d["ANIMALID"]), includeDonations=False))
    if d["MOVEMENTID"] is not None and d["MOVEMENTID"] != 0:
        tags = append_tags(tags, movement_tags(dbo, asm3.movement.get_movement(dbo, d["MOVEMENTID"])))
    tags = append_tags(tags, donation_tags(dbo, dons))
    tags = append_tags(tags, org_tags(dbo, username))
    return substitute_template(dbo, templateid, tags)

def generate_foundanimal_doc(dbo, templateid, faid, username):
    """
    Generates a found animal document from a template
    templateid: The ID of the template
    faid: The found animal to generate for
    """
    a = asm3.lostfound.get_foundanimal(dbo, faid)
    if a is None:
        raise asm3.utils.ASMValidationError("%d is not a valid found animal ID" % faid)
    tags = person_tags(dbo, asm3.person.get_person(dbo, a["OWNERID"]))
    tags = append_tags(tags, foundanimal_tags(dbo, a))
    tags = append_tags(tags, org_tags(dbo, username))
    return substitute_template(dbo, templateid, tags)

def generate_lostanimal_doc(dbo, templateid, laid, username):
    """
    Generates a found animal document from a template
    templateid: The ID of the template
    laid: The lost animal to generate for
    """
    a = asm3.lostfound.get_lostanimal(dbo, laid)
    if a is None:
        raise asm3.utils.ASMValidationError("%d is not a valid lost animal ID" % laid)
    tags = person_tags(dbo, asm3.person.get_person(dbo, a["OWNERID"]))
    tags = append_tags(tags, lostanimal_tags(dbo, a))
    tags = append_tags(tags, org_tags(dbo, username))
    return substitute_template(dbo, templateid, tags)

def generate_licence_doc(dbo, templateid, licenceid, username):
    """
    Generates a licence document from a template
    templateid: The ID of the template
    licenceid: The licence to generate for
    """
    l = asm3.financial.get_licence(dbo, licenceid)
    if l is None:
        raise asm3.utils.ASMValidationError("%d is not a valid licence ID" % licenceid)
    tags = person_tags(dbo, asm3.person.get_person(dbo, l["OWNERID"]))
    if l["ANIMALID"] is not None and l["ANIMALID"] != 0:
        tags = append_tags(tags, animal_tags(dbo, asm3.animal.get_animal(dbo, l["ANIMALID"])))
    tags = append_tags(tags, licence_tags(dbo, l))
    tags = append_tags(tags, org_tags(dbo, username))
    return substitute_template(dbo, templateid, tags)

def generate_movement_doc(dbo, templateid, movementid, username):
    """
    Generates a movement document from a template
    templateid: The ID of the template
    movementid: The movement to generate for
    """
    m = asm3.movement.get_movement(dbo, movementid)
    if m is None:
        raise asm3.utils.ASMValidationError("%d is not a valid movement ID" % movementid)
    tags = animal_tags(dbo, asm3.animal.get_animal(dbo, m["ANIMALID"]), includeDonations=False)
    if m["OWNERID"] is not None and m["OWNERID"] != 0:
        tags = append_tags(tags, person_tags(dbo, asm3.person.get_person(dbo, m["OWNERID"])))
    tags = append_tags(tags, movement_tags(dbo, m))
    tags = append_tags(tags, donation_tags(dbo, asm3.financial.get_movement_donations(dbo, movementid)))
    tags = append_tags(tags, org_tags(dbo, username))
    return substitute_template(dbo, templateid, tags)

def generate_transport_doc(dbo, templateid, transportids, username):
    """
    Generates a transport document from a template
    templateid: The ID of the template
    transportids: A list of ids to generate for
    """
    tt = asm3.movement.get_transports_by_ids(dbo, transportids)
    if len(tt) == 0: 
        raise asm3.utils.ASMValidationError("%s does not contain any valid transport IDs" % transportids)
    tags = transport_tags(dbo, tt)
    tags = append_tags(tags, org_tags(dbo, username))
    return substitute_template(dbo, templateid, tags)

def generate_waitinglist_doc(dbo, templateid, wlid, username):
    """
    Generates a waiting list document from a template
    templateid: The ID of the template
    wlid: The waiting list to generate for
    """
    a = asm3.waitinglist.get_waitinglist_by_id(dbo, wlid)
    if a is None:
        raise asm3.utils.ASMValidationError("%d is not a valid waiting list ID" % wlid)
    tags = person_tags(dbo, asm3.person.get_person(dbo, a["OWNERID"]))
    tags = append_tags(tags, waitinglist_tags(dbo, a))
    tags = append_tags(tags, org_tags(dbo, username))
    return substitute_template(dbo, templateid, tags)

