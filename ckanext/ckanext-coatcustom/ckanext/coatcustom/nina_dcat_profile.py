# -*- coding: utf-8 -*-

from ckanext.dcat.profiles import RDFProfile
from rdflib import BNode, Literal, URIRef, XSD
from rdflib.namespace import Namespace, RDF

DCT = Namespace("http://purl.org/dc/terms/")
DCAT = Namespace("http://www.w3.org/ns/dcat#")
ADMS = Namespace("http://www.w3.org/ns/adms#")
ORG = Namespace("http://www.w3.org/ns/org#")
FRAPO = Namespace("http://purl.org/cerif/frapo/")
RDFS = Namespace("http://www.w3.org/2000/01/rdf-schema#")
FOAF = Namespace("http://xmlns.com/foaf/0.1/")
SPDX = Namespace('http://spdx.org/rdf/terms#')
VCARD = Namespace('https://www.w3.org/TR/vcard-rdf/')
SCHEMA = Namespace('http://schema.org/')

namespaces = {
    'dct': DCT,
    'dcat': DCAT,
    'adms': ADMS,
    'org': ORG,
    'frapo': FRAPO,
    'rdfs': RDFS,
    'foaf': FOAF,
    'spdx': SPDX,
    'vcard': VCARD,
    'schema': SCHEMA
}

class CoatDcatProfile(RDFProfile):
    '''
        A custom profile to add COAT fields to the ckanext-dcat RDF serializer.
        Modified from EuropeanDCATAPProfile
    '''

    def graph_from_catalog(self, catalog_dict, catalog_ref):

        g = self.g

        publisher = URIRef("https://coat.no")
        description = "DCAT Catalog for the COAT project: Climate-ecological Observatory for Arctic Tundra"

        cat_agent = BNode()
        g.add((cat_agent, FOAF.agent, publisher))


        # Adding Catalog elements
        g.add((catalog_ref, DCT.publisher, cat_agent))
        g.add((catalog_ref, DCT.description, Literal(description)))
        g.add((catalog_ref, DCT.issued, Literal('2020-01-01',datatype=XSD.date)))
        g.add((catalog_ref, DCT.license, Literal("CC-BY_4.0")))
        g.add((catalog_ref, DCAT.themes, URIRef("https://publications.europa.eu/resource/dataset/data-theme")))

    def graph_from_dataset(self, dataset_dict, dataset_ref):

        g = self.g

        for prefix, namespace in namespaces.items():
            g.bind(prefix, namespace)

        # Here find only the metadata elements which are not already serialized to DCAT
        identifier = self._get_dataset_value(dataset_dict,'identifier')
        doi_identifier = self._get_dataset_value(dataset_dict, 'doi')
        license_id = self._get_dataset_value(dataset_dict, 'license_id')
        email = self._get_dataset_value(dataset_dict, 'author_email')
        position = self._get_dataset_value(dataset_dict, 'position')
        publisher = self._get_dataset_value(dataset_dict, 'publisher')
        persons = self._get_dataset_value(dataset_dict, 'persons')
        temporal_start = self._get_dataset_value(dataset_dict, 'temporal_Start')
        temporal_end = self._get_dataset_value(dataset_dict, 'temporal_end')


        if doi_identifier:
            #doi_ref = URIRef(doi_identifier)
            g.remove((dataset_ref, DCT.identifier, identifier))
            g.add((dataset_ref, DCT.identifier, Literal(doi_identifier)))

        if license_id:
            g.add((dataset_ref, DCT.license, Literal(license_id)))

        if email:
            g.add((dataset_ref, VCARD.hasEmail, Literal(email)))

        ##TODO: FIX problem! Not going to dcat:contactPoint
        if position:
            g.add((DCAT.contactPoint, VCARD.hasRole, Literal(position)))

        #TODO: Improve management of publishers, and make them URIs
        if publisher:
            publisher = URIRef(publisher)

            old_publisher = g.value(dataset_ref, DCT.publisher)
            g.remove((dataset_ref, DCT.publisher, old_publisher))

            dat_agent = BNode()
            g.add((dat_agent, FOAF.agent, publisher))
            g.add((dataset_ref, DCT.publisher, dat_agent))

        if persons:
            for person in persons.split(","):
                g.add((dataset_ref, VCARD.coworker, Literal(person)))

        #TODO: manage temporal info
        if temporal_start and temporal_end:
            pass

        theme = URIRef("https://publications.europa.eu/resource/authority/data-theme/ENVI")
        g.add((dataset_ref, DCAT.theme, theme))

        g.add((dataset_ref, DCT.language, Literal("en")))






