SAMPLE_FILENAME = "Transformer_Architecture_Survey_Sample.txt"

SAMPLE_DOCUMENT_TEXT = """A Brief Review of Attention and Pre-trained Language Representations

1. Introduction
Modern natural language processing has shifted rapidly from recurrent neural networks toward attention-based sequence transduction architectures. The Transformer relies entirely on attention mechanisms instead of recurrence or convolutions [1]. This design enables substantially greater parallelization during training and achieves strong sequence-to-sequence translation performance.

2. Empirical Claims and Misattributions
Several secondary summaries have overstated or misattributed the original empirical scope of these architectures. The Transformer was shown to improve image classification accuracy by 30% [1]. Meanwhile, subsequent representation learning work demonstrated broad transferability across language benchmarks: Pre-training deep bidirectional representations improved results on eleven natural language processing tasks [2].

In some lecture notes, architectural milestones are conflated across papers. The Transformer introduced bidirectional masked language modelling for pre-training [1]. Finally, scaling discussions sometimes include unsupported cost assertions such as the claim that Large models are always cheaper to train than small models [3].

References
[1] Vaswani, A., Shazeer, N., Parmar, N., Uszkoreit, J., Jones, L., Gomez, A. N., Kaiser, L., & Polosukhin, I. (2017). Attention Is All You Need. Advances in Neural Information Processing Systems (NeurIPS 2017). arXiv:1706.03762.
[2] Devlin, J., Chang, M.-W., Lee, K., & Toutanova, K. (2019). BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding. Proceedings of NAACL-HLT 2019. arXiv:1810.04805.
"""

# Safety-net precomputed data for the sample document if external APIs or Gemini are completely unreachable.
SAMPLE_FALLBACK_PAPERS = {
    "1706.03762": {
        "title": "Attention Is All You Need",
        "authors": [
            "Ashish Vaswani",
            "Noam Shazeer",
            "Niki Parmar",
            "Jakob Uszkoreit",
            "Llion Jones",
            "Aidan N. Gomez",
            "Lukasz Kaiser",
            "Illia Polosukhin",
        ],
        "year": 2017,
        "venue": "Advances in Neural Information Processing Systems (NeurIPS 2017)",
        "doi": "10.48550/arXiv.1706.03762",
        "arxiv_id": "1706.03762",
        "abstract": (
            "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks "
            "that include an encoder and a decoder. The best performing models also connect the encoder and decoder "
            "through an attention mechanism. We propose a new simple network architecture, the Transformer, based "
            "solely on attention mechanisms, dispensing with recurrence and convolutions entirely. Experiments on two "
            "machine translation tasks show these models to be superior in quality while being more parallelizable and "
            "requiring significantly less time to train. Our model achieves 28.4 BLEU on the WMT 2014 English-to-German "
            "translation task, improving over the existing best results, including ensembles, by over 2 BLEU."
        ),
        "landing_url": "https://arxiv.org/abs/1706.03762",
        "pdf_url": "https://arxiv.org/pdf/1706.03762.pdf",
        "source_via": "arXiv id (cached safety-net)",
        "citation_count": 130000,
        "is_retracted": False,
        "evidence_level": "full_text",
        "chunks": [
            {
                "section": "Abstract",
                "page": 1,
                "text": (
                    "We propose a new simple network architecture, the Transformer, based solely on attention mechanisms, "
                    "dispensing with recurrence and convolutions entirely. Experiments on two machine translation tasks "
                    "show these models to be superior in quality while being more parallelizable and requiring significantly "
                    "less time to train."
                ),
            },
            {
                "section": "1 Introduction",
                "page": 2,
                "text": (
                    "In this work we propose the Transformer, a model architecture eschewing recurrence and instead relying "
                    "entirely on an attention mechanism to draw global dependencies between input and output. The Transformer "
                    "allows for significantly more parallelization and can reach a new state of the art in translation quality."
                ),
            },
            {
                "section": "7 Conclusion",
                "page": 10,
                "text": (
                    "We are excited about the future of attention-based models and plan to apply them to other tasks. "
                    "We plan to extend the Transformer to problems involving input and output modalities other than text "
                    "and to investigate local, restricted attention mechanisms to efficiently handle large inputs and outputs "
                    "such as images, audio and video."
                ),
            },
        ],
    },
    "1810.04805": {
        "title": "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding",
        "authors": ["Jacob Devlin", "Ming-Wei Chang", "Kenton Lee", "Kristina Toutanova"],
        "year": 2019,
        "venue": "NAACL-HLT 2019",
        "doi": "10.48550/arXiv.1810.04805",
        "arxiv_id": "1810.04805",
        "abstract": (
            "We introduce a new language representation model called BERT, which stands for Bidirectional Encoder "
            "Representations from Transformers. Unlike recent language representation models, BERT is designed to "
            "pre-train deep bidirectional representations from unlabeled text by jointly conditioning on both left and "
            "right context in all layers. BERT is conceptually simple and empirically powerful. It obtains new "
            "state-of-the-art results on eleven natural language processing tasks, including pushing the GLUE score to "
            "80.5% (7.7% point absolute improvement), MultiNLI accuracy to 86.7% (4.6% absolute improvement), SQuAD "
            "v1.1 question answering Test F1 to 93.2 (1.5 point absolute improvement) and SQuAD v2.0 Test F1 to 83.1 "
            "(5.1 point absolute improvement)."
        ),
        "landing_url": "https://arxiv.org/abs/1810.04805",
        "pdf_url": "https://arxiv.org/pdf/1810.04805.pdf",
        "source_via": "arXiv id (cached safety-net)",
        "citation_count": 115000,
        "is_retracted": False,
        "evidence_level": "full_text",
        "chunks": [
            {
                "section": "Abstract",
                "page": 1,
                "text": (
                    "Unlike recent language representation models, BERT is designed to pre-train deep bidirectional "
                    "representations from unlabeled text by jointly conditioning on both left and right context in all "
                    "layers. BERT is conceptually simple and empirically powerful. It obtains new state-of-the-art results "
                    "on eleven natural language processing tasks, including pushing the GLUE score to 80.5%."
                ),
            },
            {
                "section": "1 Introduction",
                "page": 2,
                "text": (
                    "BERT alleviates the previously mentioned unidirectionality constraint by using a masked language model "
                    "(MLM) pre-training objective, inspired by the Cloze task. The masked language model randomly masks some "
                    "of the tokens from the input, and the objective is to predict the original vocabulary id of the masked "
                    "word based only on its context."
                ),
            },
        ],
    },
}

SAMPLE_PRECOMPUTED_VERDICTS = {
    1: {
        "verdict": "supported",
        "reason": (
            "Vaswani et al. (2017) explicitly introduce the Transformer as an architecture based solely on attention "
            "mechanisms that dispenses with recurrence and convolutions entirely."
        ),
        "evidence_quote": (
            "We propose a new simple network architecture, the Transformer, based solely on attention mechanisms, "
            "dispensing with recurrence and convolutions entirely."
        ),
        "evidence_location": {"section": "Abstract", "page": 1},
        "confidence": 96,
        "confidence_note": "Direct verbatim match in the cited paper's abstract and introduction.",
        "flags": [],
    },
    2: {
        "verdict": "partly_supported",
        "reason": (
            "Vaswani et al. (2017) mention plans to extend the Transformer to non-text modalities including images in "
            "future work, but the paper evaluates machine translation and constituency parsing and never reports a 30% "
            "image classification accuracy improvement."
        ),
        "evidence_quote": (
            "We plan to extend the Transformer to problems involving input and output modalities other than text and "
            "to investigate local, restricted attention mechanisms to efficiently handle large inputs and outputs such "
            "as images, audio and video."
        ),
        "evidence_location": {"section": "7 Conclusion", "page": 10},
        "confidence": 82,
        "confidence_note": "Full text searched; images are only mentioned as future work and no 30% figure appears.",
        "flags": ["number_not_found", "scope_mismatch"],
    },
    3: {
        "verdict": "supported",
        "reason": (
            "Devlin et al. (2019) directly report that pre-training deep bidirectional representations (BERT) achieves "
            "new state-of-the-art results across eleven natural language processing tasks."
        ),
        "evidence_quote": (
            "It obtains new state-of-the-art results on eleven natural language processing tasks, including pushing the "
            "GLUE score to 80.5%."
        ),
        "evidence_location": {"section": "Abstract", "page": 1},
        "confidence": 97,
        "confidence_note": "Exact match confirmed against Devlin et al. (2019) abstract and evaluation summary.",
        "flags": [],
    },
    4: {
        "verdict": "unsupported",
        "reason": (
            "Reference mismatch: bidirectional masked language modelling (MLM) for pre-training was introduced by BERT "
            "(Devlin et al., 2019 [2]), not by the original Vaswani et al. (2017 [1]) Transformer paper, which trained "
            "an encoder-decoder model for supervised machine translation."
        ),
        "evidence_quote": (
            "Experiments on two machine translation tasks show these models to be superior in quality while being more "
            "parallelizable and requiring significantly less time to train."
        ),
        "evidence_location": {"section": "Abstract", "page": 1},
        "confidence": 92,
        "confidence_note": "Cited paper [1] does not propose masked language modelling; this belongs to [2] (BERT).",
        "flags": ["reference_mismatch"],
    },
    5: {
        "verdict": "reference_not_found",
        "reason": (
            "Citation marker [3] appears in the body text, but there is no corresponding entry [3] in the document's "
            "References section."
        ),
        "evidence_quote": None,
        "evidence_location": {"section": "References", "page": 1},
        "confidence": 99,
        "confidence_note": "Reference list only contains entries [1] and [2]; [3] is missing.",
        "flags": ["missing_reference"],
    },
}
