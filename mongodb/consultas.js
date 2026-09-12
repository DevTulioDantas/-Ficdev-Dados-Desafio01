

// Consultas de demonstração da coleção comentarios_avaliacoes (RF07)
// Rodar com: mongosh <uri> desafio_dados/mongodb/consultas.js
// =====================================================================

// 1. Inserir um documento 

db.comentarios_avaliacoes.insertOne({
    usuario_id: 104,
    conteudo_id: 28,
    avaliacao: 5,
    comentario: "Conteúdo introdutório, claro e objetivo.",
    tags: ["didatico", "iniciante", "python"],
    data: "2026-08-20",
});

// 2. Consultar todos os comentários de um determinado conteúdo
db.comentarios_avaliacoes.find({ conteudo_id: 28 });

// 3. Localizar documentos por tag
db.comentarios_avaliacoes.find({ tags: "iniciante" });

// 4. Filtrar avaliações por nota (ex: só notas 4 e 5)
db.comentarios_avaliacoes.find({ avaliacao: { $gte: 4 } });

// 5. Agregar quantidade de comentários/avaliações por conteúdo
//    (a categoria não existe no Mongo — ela vive no PostgreSQL. Este
//    agrupamento por conteudo_id é a base; o cruzamento com a
//    categoria de cada conteudo_id é feito no lado do PostgreSQL/
//    persistencia/mongo.py, já que exige um join entre os dois bancos)
db.comentarios_avaliacoes.aggregate([
    {
        $group: {
            _id: "$conteudo_id",
            quantidade_comentarios: { $sum: 1 },
            media_avaliacao: { $avg: "$avaliacao" },
        },
    },
    { $sort: { quantidade_comentarios: -1 } },
]);