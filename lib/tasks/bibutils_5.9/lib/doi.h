/*
 * doi.h
 *
 * Copyright (c) Chris Putnam 2004-2016
 *
 * Source code released under the GPL version 2
 *
 */
#ifndef DOI_H
#define DOI_H

#include "newstr.h"
#include "fields.h"

int is_doi( char *s );
int is_uri_remote_scheme( char *p );
int is_embedded_link( char *s );

void doi_to_url( fields *info, int n, char *urltag, newstr *doi_url );
void pmid_to_url( fields *info, int n, char *urltag, newstr *pmid_url );
void pmc_to_url( fields *info, int n, char *urltag, newstr *pmid_url );
void arxiv_to_url( fields *info, int n, char *urltag, newstr *arxiv_url );
void jstor_to_url( fields *info, int n, char *urltag, newstr *jstor_url );

#endif
