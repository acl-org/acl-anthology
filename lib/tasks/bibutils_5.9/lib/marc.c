/*
 * marc.c
 *
 * Copyright (c) Chris Putnam 2004-2016
 *
 * Source code released under the GPL version 2
 *
 */
#include "marc.h"
#include <string.h>

int
marc_findgenre( char *query )
{
	char *marc[] = { 
		"abstract or summary",
		"art original", 
		"art reproduction",
		"article",
		"atlas",
		"autobiography", 
		"bibliography",
		"biography",
		"book",
		"calendar",
		"catalog", 
		"chart",
		"comic or graphic novel",
		"comic strip",
		"conference publication",
		"database",
		"dictionary",
		"diorama",
		"directory",
		"discography",
		"drama",
		"encyclopedia",
		"essay",
		"festschrift",
		"fiction",
       		"filmography",
		"filmstrip",
		"finding aid",
		"flash card",
		"folktale",
		"font",
		"game",
		"government publication",
		"graphic",
		"globe",
		"handbook",
		"history",
		"humor, satire",
		"hymnal",
		"index",
		"instruction",
		"interview",
		"issue",
		"journal",
		"kit",
		"language instruction",
		"law report or digest",
		"legal article",
		"legal case and case notes",
		"legislation",
		"letter",
		"loose-leaf",
		"map",
		"memoir",
		"microscope slide",
		"model",
		"motion picture",
		"multivolume monograph",
		"newspaper",
		"novel",
		"numeric data",
		"offprint",
		"online system or service",
		"patent",
		"periodical",
		"picture",
		"poetry",
		"programmed text",
		"realia",
		"rehearsal",
		"remote sensing image",
		"reporting",
		"review",
		"series",
		"short story",
		"slide",
		"sound",
		"speech",
		"standard or specification",
		"statistics",
		"survey of literature",
		"technical drawing",
		"technical report",
		"thesis",
		"toy",
		"transparency",
		"treaty",
		"videorecording",
		"web site",
		"yearbook",
	};
	int nmarc = sizeof( marc ) / sizeof( char* );
	int i;
	for ( i=0; i<nmarc; ++i ) {
		if ( !strcasecmp( query, marc[i] ) ) return i;
	}
	return -1;
}

int
marc_findresource( char *query )
{
	char *marc[] = { 
		"cartographic",
		"kit",
		"mixed material",
		"moving image",
		"notated music",
		"software, multimedia",
		"sound recording",
		"sound recording - musical",
		"sound recording - nonmusical",
		"still image",
		"text",
		"three dimensional object"
	};
	int nmarc = sizeof( marc ) / sizeof( char* );
	int i;
	for ( i=0; i<nmarc; ++i ) {
		if ( !strcasecmp( query, marc[i] ) ) return i;
	}
	return -1;
}
